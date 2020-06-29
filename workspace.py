import networkx as nx
import os
import json
import re
import subprocess
import argparse
import yaml
from pathlib import Path

class PackageDescriptor:
    def __init__(self, value):
        if ("requires" in value):
            self.deps = value["requires"]
        else:
            self.deps = []
        self.package_reference = PackageReference.from_string(value["pref"])

    def name(self):
        return self.package_reference.name

    def semantic_version(self):
        return self.package_reference.semantic_version

    def revision(self):
        return self.package_reference.revision

    def user(self):
        return self.package_reference.user

    def channel(self):
        return self.package_reference.channel

    def dependencies(self):
        return [] + self.deps

class Editable:
    def __init__(self, package, path, layout):
        self.package = package
        self.path = path
        self.layout = layout

    def disable(self):
        subprocess.run('conan', 'editable', 'remove', self.package.name + '/' + self.package.main_revision())

class Package:
    def __init__(self, name, workspace):
        self.name = name
        self.workspace = workspace

    def directory(self):
        return os.path.join(self.workspace.root, self.name)

    def commit(self):
        directory = self.directory()
        subprocess.run(['git', 'add', 'conanfile.py'], stdout=subprocess.PIPE, cwd=directory)
        commit = subprocess.run(['git', 'commit', '-m', 'Version bump'], stdout=subprocess.PIPE, cwd=directory)
        return self.git_revision()

    def main_semantic_version(self):
        return self.workspace.main_references[self.name].semantic_version

    def main_revision(self):
        return self.workspace.main_references[self.name].revision

    def main_user(self):
        return self.workspace.main_references[self.name].user

    def main_channel(self):
        return self.workspace.main_references[self.name].channel

    def git_revision(self):
        hash = subprocess.run(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE, cwd=self.directory())
        return hash.stdout.rstrip().decode('utf-8')

    def is_downloaded(self):
        return os.path.exists(os.path.join(self.workspace.root, self.name))

    def is_editable(self):
        return self.name in self.workspace.editables()

    def editable(self) -> Editable:
        editables = self.workspace.editables()
        return editables[self.name] if self.name in editables else None

class PackageReference:

    @classmethod
    def from_string(self, reference_string):
        name_match = re.search('([^@]+)/', reference_string)
        name = name_match.group(1)

        revision_match = re.search('/([^@]*)\.([a-z0-9]*)', reference_string)
        semantic_version = revision_match.group(1)
        revision = revision_match.group(2)

        user_match = re.search('@([a-zA-Z]*)', reference_string)
        user = user_match.group(1) if user_match else None

        channel_match = re.search('@[a-zA-Z]*/([a-zA-Z]*)', reference_string)
        channel = channel_match.group(1) if channel_match else None
        return PackageReference(name, semantic_version, revision, user, channel)

    def __init__(self, name, semantic_version, revision, user, channel):
        self.name = name
        self.semantic_version = semantic_version
        self.revision = revision
        self.user = user
        self.channel = channel

class Workspace:
    def __init__(self, main, root):
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
                pkg = PackageDescriptor(value)
                name = pkg.name()
                graph.add_node(name)
                semantic_version = pkg.semantic_version()
                revision = pkg.revision()
                user = pkg.user()
                channel = pkg.channel()
                references[name] = PackageReference(name, semantic_version, revision, user, channel)
                msg = "Found package " + name + " with revision: " + pkg.revision()
                if (user) : msg = msg + " user: " + user + " channel: " + channel
                print(msg)


            for index, value in packages.items():
                pkg = PackageDescriptor(value)
                dependencies = pkg.dependencies()
                for dependency in dependencies:
                    dep = packages[dependency]
                    dep_pkg = PackageDescriptor(dep)
                    graph.add_edge(pkg.name(), dep_pkg.name())
        return graph, references

    def package(self, package_name):
        if (not self.has_package(package_name)):
            raise Exception("The workspace does not have a package named " + package_name)
        return Package(package_name, self)

    def has_package(self, package_name):
        return self.graph.has_node(package_name)

    def package_order(self):
        graph = self.graph
        sort = nx.topological_sort(graph)
        return reversed(list(sort))

    def commit_and_propagate_hash(self, package_name):
        package = self.package(package_name)
        if (package.is_downloaded()):
            import fileinput
            hash = package.commit()
            for dependency_name in nx.ancestors(self.graph, package_name):
                dependency = self.package(dependency_name)
                regex = re.compile(package_name + '/(.*)\.([a-z0-9]*)')
                if (dependency.is_downloaded()):
                    print("Setting requirement revision of " + package_name + " to " + hash + " in " + dependency_name)
                    for line in fileinput.input(os.path.join(dependency.directory(), "conanfile.py"), inplace=True):
                        newcontent = re.sub(regex, package_name + r'/\1.' + hash, line)
                        print(newcontent, end="")

    def commit_and_propagate_hashes(self):
        for package in self.package_order():
            self.commit_and_propagate_hash(package)

    def download(self, package_name):
        package = self.package(package_name)
        if (not os.path.exists(os.path.join(package.directory(), ".git"))):
            repo = self.git_prefix + package_name + self.git_suffix
            print("Cloning repository " + repo)
            subprocess.run(['git', 'clone', repo, package_name], stdout=subprocess.PIPE, cwd=self.root)
            subprocess.run(['git', 'checkout', package.main_revision()], stdout=subprocess.PIPE, cwd=package.directory())
            editable = package.editable()
            if (editable):
                editable.disable()

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
                        package_revision = pkg.main_revision()
                        test = pkg.main_revision() == package_reference.revision
                        if (pkg.main_semantic_version() ==  package_reference.semantic_version and pkg.main_revision() == package_reference.revision and pkg.main_user() == package_reference.user and pkg.main_channel() == package_reference.channel):
                            result[key] = Editable(pkg, value["path"], value["layout"])
        return result

def main():
    parser = argparse.ArgumentParser(description='Manage a feature branch workspace.')
    subparsers = parser.add_subparsers(help='sub-command help', dest='command')
    parser_bump = subparsers.add_parser('bump', help='bump help')
    parser_bump.add_argument('project', nargs='?')
    parser_download = subparsers.add_parser('download', help='download help')
    parser_download.add_argument('project')
    parser.add_argument('-m', '--main', type=str, required=False)

    args = parser.parse_args()
    workspace = Workspace(args.main, os.getcwd())

    for key, value in workspace.editables().items():
        print("Editable for " + key)

    if (args.command == 'bump'):
        project = workspace.main
        if(args.project and len(args.project) == 1):
            project = args.project[0]
        print('Bumping packaging revisions.')
        workspace.commit_and_propagate_hashes()
    elif (args.command == 'download'):
        workspace.download(args.project)

main()