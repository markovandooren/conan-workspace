import subprocess
import os
from workspace.git import *
from workspace.editable import *
from pathlib import Path

class Package:
    def __init__(self, name, workspace):
        self.name = name
        self.workspace = workspace
        self.git = Git(self.directory())

    def directory(self):
        return os.path.join(self.workspace.root, self.name)

    def commit(self, commit_message = None):
        """
        Commit the current package if it is dirty.

        Return the new revision if a commit was done,
        or the existing revision if no commit was done.
        """
        if self.git.is_dirty():
            self.git.add('conanfile.py')
            self.git.commit('Requirements version bump' if not commit_message else commit_message)
        return self.git.revision()

    def main_semantic_version(self):
        return self.workspace.main_references[self.name].semantic_version

    def main_sequence_in_branch(self):
        return self.workspace.main_references[self.name].sequence_in_branch

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

    def toggle_editable(self):
        if self.is_editable():
            subprocess.run(['conan', 'editable', 'remove', self.main_reference()])
        else:
            subprocess.run(['conan', 'editable', 'add', str(Path(self.directory(), 'conanfile.py')), str(self.main_reference())])

    def edit(self, actual = False):
        if self.is_downloaded():
            ref = self.workspace.main_references[self.name]
            if actual:
                ref = ref.clone(self.git.sequence_in_branch(), self.git.revision())
            subprocess.run(['conan', 'editable', 'add', self.directory(), ref.to_string()], cwd=self.workspace.root)

    def close(self):
        if self.is_editable():
            self.editable().disable()

    def has_valid_revision(self):
        return self.git.contains(self.main_revision())

    def can_be_updated_after_merge(self):
        """
        Check if this package can be updated to a more stable branch that contains
        the current commit.
        """
        current_revision = self.git.revision()
        most_stable_branch, most_stable_revision = self.git.most_stable_remote_branch_containing(current_revision)
        return current_revision != most_stable_revision

    def update_to_most_stable_version(self):
        """
        Find the most stable revision that contains the current revision, and if
        it is different from the current revision. Checkout that branch and peg
        the new revision in the workspace.
        """
        current_revision = self.git.revision()
        most_stable_branch, most_stable_revision = self.git.most_stable_remote_branch_containing(current_revision)
        if current_revision != most_stable_revision:
            # 1. Check out the most stable revision at its branch.
            self.git.force_create_branch(most_stable_branch, most_stable_revision)
            self.git.checkout_branch(most_stable_branch)
            # 2. Update the upstream dependencies to now refer to this revision.
            self.workspace.peg_package(self.name)
