#!/usr/bin/env python
import networkx as nx
import json
import argparse
import yaml
from pathlib import Path
from workspace.ui import *
from workspace.package import *
from workspace.editable import *
from workspace.packagereference import *

class Workspace:
    """
    A workspace is consistent when all of the following are true.
        * forall p in downloaded packages : conan install is successfull
        * forall p in downloaded packages : p.is_editable() and p.editable.directory == p.directory()
        * forall p in downloaded packages : p.git.revision() contains p.main_revision()
        * forall p in downloaded packages : p.git.branch() == main.git.branch()
    """
    def __init__(self, main, root):
        self.yaml = None
        if (os.path.exists(os.path.join(root, "workspace.yml"))):
            with open(os.path.join(root, "workspace.yml")) as stream:
                self.yaml = yaml.safe_load(stream)
                self.git_prefix = self.yaml["git_prefix"] if "git_prefix" in self.yaml else ""
                self.git_suffix = self.yaml["git_suffix"] if "git_suffix" in self.yaml else ""
                if self.git_prefix == None : self.git_prefix = ""
                if self.git_suffix == None : self.git_suffix = ""
        if (main):
            self.main = main
        elif (self.yaml and "main" in self.yaml):
            self.main = self.yaml["main"]
        else:
            max_size = 0
            with os.scandir(root) as dirs:
                for entry in dirs:
                    if (entry.is_dir() and os.path.exists(os.path.join(entry.path, "conan.lock"))):
                        size = os.path.getsize(os.path.join(entry.path, "conan.lock"))
                        if (size > max_size) :
                            max_size = size
                            self.main = entry.name
            if (max_size == 0):
                raise Exception('The main project could not be determined.')
            print("Auto-detected main based on conan.lock file size: " + self.main)
        self.main_directory = os.path.join(root, self.main)
        self.root = root
        self.update_graph()

    def update_graph(self):
        self.graph, self.main_references = self.read_graph()

    def read_graph(self):
        graph = nx.DiGraph()
        references = {}

        with open(os.path.join(self.main_directory, "conan.lock")) as json_file:
            data = json.load(json_file)
            packages = data["graph_lock"]["nodes"]

            for index, value in packages.items():
                descriptor = PackageDescriptor(value)
                name = descriptor.name
                graph.add_node(name)
                semantic_version = descriptor.semantic_version
                sequence_in_branch = descriptor.sequence_in_branch
                revision = descriptor.revision
                user = descriptor.user
                channel = descriptor.channel
                references[name] = PackageReference(name, semantic_version, sequence_in_branch, revision, user, channel)

            for index, value in packages.items():
                descriptor = PackageDescriptor(value)
                dependencies = descriptor.dependencies
                for dependency in dependencies:
                    dep = packages[dependency]
                    dep_pkg = PackageDescriptor(dep)
                    graph.add_edge(descriptor.name, dep_pkg.name)
        return graph, references

    def package(self, package_name):
        if (not self.has_package(package_name)):
            raise Exception("The workspace does not have a package named " + package_name)
        return Package(package_name, self)

    def has_package(self, package_name):
        return self.graph.has_node(package_name)

    def reversed_package_name_order(self):
        return reversed(self.package_name_order())

    def package_name_order(self):
        graph = self.graph
        sort = nx.topological_sort(graph)
        return list(sort)

    def packages(self):
        nodes = self.graph.nodes
        return [ Package(name, self) for name in nodes ]

    def close(self):
        for name, editable in self.editables().items():
            editable.disable()

    def edit(self, actual):
        for package in self.packages():
            package.edit(actual)

    def peg_package(self, package_name, commit_message = None):
        package = self.package(package_name)
        if package.is_downloaded() and package.is_editable():
            import fileinput

            # Commit the package and obtain the new revision.
            hash = package.commit(commit_message)
            sequence_in_branch = package.git.sequence_in_branch()
            # Remove the editable for the old revision.
            editable = package.editable()
            if (editable):
                editable.disable()

            # Add the editable for the new revision.
            new_package_reference = package.main_reference().clone(sequence_in_branch, hash)
            new_editable = Editable(new_package_reference, package.directory(), None)
            new_editable.edit()

            # Update the revision in the conanfiles that depend on this package and install their dependencies.
            for dependency_name in nx.ancestors(self.graph, package_name):
                dependency = self.package(dependency_name)
                if dependency.is_downloaded() and dependency.is_editable():
                    regex = re.compile(package_name + '/(.*)\.([0-9]+)\.([a-z0-9]{40})')
                    # Use the new revision in the conanfile. We substitute regardless of whether it uses it directly.
                    print("Setting requirement revision of " + package_name + " to " + hash + " in " + dependency_name)
                    for line in fileinput.input(os.path.join(dependency.directory(), "conanfile.py"), inplace=True):
                        newcontent = re.sub(regex, package_name + r'/\1.' + str(sequence_in_branch) + '.' + hash, line)
                        print(newcontent, end="")
                    # Install the package again such that Conan call still work correctly for that package.

    def peg(self, commit_message = None):
        if commit_message and len(commit_message) == 0:
            commit_message = None
        packages = self.packages()
        # The packages will update their editables before install is ran on the main package.
        # That means that we have to check for editability beforehand. Otherwise, we can't figure
        # out on which packages to run conan install afterwards.
        editable_packages_names = [package.name for package in packages if package.is_downloaded() and package.is_editable()]
        for package in packages:
            if package.is_editable() and not package.has_valid_revision():
                raise Exception('Package %s does not have a valid revision.' % package.name)
        if not commit_message:
            for package in packages:
                if package.git.is_dirty():
                    raise Exception('Package %s has local changes. Peg is not allowed without a commit message.' % package.name)

        for package_name in self.reversed_package_name_order():
            self.peg_package(package_name, commit_message if package.git.is_dirty() else None)
        # We install the packages again after changing all of the dependencies to
        # avoid doing it a quadratic number of times.
        for package_name in self.reversed_package_name_order():
            package = self.package(package_name)
            if package_name in editable_packages_names:
                subprocess.run(['conan', 'install', '.'], cwd=package.directory())
        # In case the workspace object is kept alive, we update the graph.
        self.update_graph()

    def download(self, package_name):
        package = self.package(package_name)
        if not os.path.exists(os.path.join(package.directory(), ".git")):
            repo = self.git_prefix + package_name + self.git_suffix
            print("Cloning repository " + repo)
            subprocess.run(['git', 'clone', repo, package_name], stdout=subprocess.PIPE, cwd=self.root)
            main_branch = self.package(self.main).git.branch()
            if main_branch :
                local_package_branches = package.git.local_branches()
                if main_branch in local_package_branches:
                    package.git.checkout_branch(main_branch)
                else:
                    package.git.checkout(package.main_revision())
                    package.git.create_branch(main_branch)
            else:
                package.git.checkout(package.main_revision())
            subprocess.run([ 'conan', 'install', '.' ], cwd=package.directory())
            subprocess.run([ 'conan', 'source', '.' ], cwd=package.directory())
            package.edit()

    def fetch(self):
        for package in self.packages():
            if package.is_downloaded() and package.is_editable():
                package.git.fetch()

    def editables(self):
        """ Return the editables of this workspace. """
        result = {}
        editable_packages_file = os.path.join(Path.home(), ".conan", "editable_packages.json")
        if (os.path.exists(editable_packages_file)):
            with open(editable_packages_file) as json_file:
                editables_dictionary = json.load(json_file)
                for key, value in editables_dictionary.items():
                    package_reference = PackageReference.from_string(key)
                    if (self.has_package(package_reference.name)):
                        pkg = self.package(package_reference.name)
                        if (pkg.main_semantic_version() ==  package_reference.semantic_version and pkg.main_revision() == package_reference.revision and pkg.main_user() == package_reference.user and pkg.main_channel() == package_reference.channel):
                            result[pkg.name] = Editable(pkg.main_reference(), value["path"], value["layout"])
        return result

def main():
    parser = argparse.ArgumentParser(description='Manage a feature branch workspace.')
    subparsers = parser.add_subparsers(help='sub-command help', dest='command')
    parser_peg = subparsers.add_parser('peg', help='peg the revision of a package or all packages')
    parser_peg.add_argument('--push', action="store_true")

    # Download
    parser_download = subparsers.add_parser('download', help='download help')
    parser_download.add_argument('package')
    parser.add_argument('-m', '--main', type=str, required=False)

    # Edit
    parser_edit = subparsers.add_parser('edit', help='Make the specified packages editable. If no packages are provided, all packages in the workspace are made editable.')
    parser_edit.add_argument('package', nargs='*')
    parser_edit.add_argument('--actual', action="store_true")

    # List
    parser_list = subparsers.add_parser('list', help='List all packages in the workspace')
    parser_list.add_argument('--revision', action="store_true")
    parser_list.add_argument('--branch', action="store_true")
    parser_list.add_argument('--branches', action="store_true")
    parser_list.add_argument('--upstream', action="store_true")
    parser_list.add_argument('--remotes', action="store_true")

    # Close
    parser_close = subparsers.add_parser('close', help='Remove the editable for the specified packages. If not packages are provided, the editable is removed for all packages in the workspace.')
    parser_close.add_argument('package', nargs='*')

    args = parser.parse_args()
    workspace = Workspace(args.main, os.getcwd())

    if (args.command == 'peg'):
        workspace.peg()
        if (args.push):
            for package_name in workspace.reversed_package_name_order():
                package = workspace.package(package_name)
                package.git.push()

    elif (args.command == 'download'):
        workspace.download(args.package)
        workspace.package(args.package).edit()
    elif (args.command == 'edit'):
        if not args.package:
            workspace.edit(args.actual)
        else:
            for package_name in args.package:
                workspace.package(package_name).edit(args.actual)
    elif (args.command == 'list'):
        for package_name in workspace.package_name_order():
            package = workspace.package(package_name)
            reference_string = package.main_reference().to_string()
            msg = reference_string

            if (args.revision):
                sequence_in_branch = package.git.sequence_in_branch()
                revision_string = package.git.revision()
                msg = msg + " : " + str(sequence_in_branch) + ' : ' + revision_string
            if (args.branch and not args.branches):
                branch_name = package.git.branch()
                if (branch_name):
                    msg = msg + " : " + branch_name
                else:
                    msg = msg + " is detached"
            if (args.branches):
                branches = package.git.current_branches()
                if len(branches) == 0:
                    msg = msg + " is detached"
                else:
                    msg = msg + " : " + (", ".join(branches))
            if (args.upstream):
                upstream_branch_name = package.git.upstream_branch()
                if (upstream_branch_name):
                    msg = msg + " : " + upstream_branch_name
                else:
                    msg = msg + " has no upstream branch"
            if (args.remotes):
                remotes = package.git.remotes()
                msg = msg + " : " + (". ".join(remotes))


            print(msg)
    elif (args.command == 'close'):
        if not args.package:
            workspace.close()
        else:
            for package_name in args.package:
                workspace.package(package_name).close()
    else:
        ui = UI(workspace)
        ui.run()

class PackageDescriptor:
    def __init__(self, value):
        if ("requires" in value):
            self.deps = value["requires"]
        else:
            self.deps = []
        self.package_reference = PackageReference.from_string(value["pref"])

    @property
    def name(self):
        return self.package_reference.name

    @property
    def semantic_version(self):
        return self.package_reference.semantic_version

    @property
    def sequence_in_branch(self):
        return self.package_reference.sequence_in_branch

    @property
    def revision(self):
        return self.package_reference.revision

    @property
    def user(self):
        return self.package_reference.user

    @property
    def channel(self):
        return self.package_reference.channel

    @property
    def dependencies(self):
        return [] + self.deps


if __name__ == '__main__':
    main()