import networkx as nx
import os
import json
import re
import subprocess
import argparse
import yaml

class PackageDescriptor:
    def __init__(self, value):
        if ("requires" in value):
            self.deps = value["requires"]
        else:
            self.deps = []
        self.pref = value["pref"]

    def name(self):
        match = re.search('(.+)/', self.pref)
        return match.group(1)

    def revision(self):
        match = re.search('/.*\.([a-z0-9]*)', self.pref)
        return match.group(1)

    def user(self):
        match = re.search('@([a-zA-Z]*)', self.pref)
        return match.group(1) if match else None

    def channel(self):
        match = re.search('@[a-zA-Z]*/([a-zA-Z]*)', self.pref)
        return match.group(1) if match else None

    def dependencies(self):
        return [] + self.deps


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

    def main_revision(self):
        return self.workspace.main_references[self.name].name

    def git_revision(self):
        hash = subprocess.run(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE, cwd=self.directory())
        return hash.stdout.rstrip().decode('utf-8')

    def is_downloaded(self):
        return os.path.exists(os.path.join(self.workspace.root, self.name))

class PackageReference:
    def __init__(self, name, revision, user, channel):
        self.name = name
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
                references[pkg.name()] = PackageReference(pkg.name(), pkg.revision(), pkg.user(), pkg.channel())
                print("Found package " + name + " with revision " + pkg.revision())

            for index, value in packages.items():
                pkg = PackageDescriptor(value)
                dependencies = pkg.dependencies()
                for dependency in dependencies:
                    dep = packages[dependency]
                    dep_pkg = PackageDescriptor(dep)
                    graph.add_edge(pkg.name(), dep_pkg.name())
        return graph, references

    def package(self, package_name):
        if (not self.graph.has_node(package_name)):
            raise Exception("The workspace does not have a package named " + package_name)
        return Package(package_name, self)

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
    if (args.command == 'bump'):
        project = workspace.main
        if(args.project and len(args.project) == 1):
            project = args.project[0]
        print('Bumping packaging revisions.')
        workspace.commit_and_propagate_hashes()
    elif (args.command == 'download'):
        workspace.download(args.project)

main()