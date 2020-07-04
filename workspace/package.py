import subprocess
import os
from workspace.git import *
from workspace.editable import *

class Package:
    def __init__(self, name, workspace):
        self.name = name
        self.workspace = workspace
        self.git =Git(self.directory())

    def directory(self):
        return os.path.join(self.workspace.root, self.name)

    def commit(self):
        directory = self.directory()
        self.git.add('conanfile.py')
        self.git.commit('Update bump')
        return self.git.revision()

    def main_semantic_version(self):
        return self.workspace.main_references[self.name].semantic_version

    def main_revision(self):
        return self.workspace.main_references[self.name].revision

    def main_user(self):
        return self.workspace.main_references[self.name].user

    def main_channel(self):
        return self.workspace.main_references[self.name].channel

    def main_reference(self):
        return self.workspace.main_references[self.name]

    def is_downloaded(self):
        return os.path.exists(os.path.join(self.workspace.root, self.name))

    def is_editable(self):
        return self.name in self.workspace.editables()

    def editable(self) -> Editable:
        editables = self.workspace.editables()
        return editables[self.name] if self.name in editables else None

    def edit(self):
        ref = self.workspace.main_references[self.name].to_string()
        subprocess.run(['conan', 'editable', 'add', self.directory(), ref], cwd=self.workspace.root)

    def push(self):
        subprocess.run(['git', 'push'], cwd=self.directory())

    def checkout(self, revision):
        subprocess.run(['git', 'checkout', revision], stdout=subprocess.PIPE, cwd=self.directory())