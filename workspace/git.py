import subprocess

class Git:
    def __init__(self, directory):
        self.directory = directory

    def git_run(self, args):
        return subprocess.run(['git'] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.directory)

    def decode_stdout(self, completed_process):
        return completed_process.stdout.rstrip().decode('utf-8')

    def git(self, args):
        return self.decode_stdout(self.git_run(args))

    def add(self, file):
        return self.git(['add', file])

    def commit(self, message):
        self.git(['commit', '-m', message])

    def revision(self):
        return self.revision_of('HEAD')

    def is_ancestor(self, potential_ancestor, commit):
        completed_process = self.git_run(['merge-base', '--is-ancestor', potential_ancestor, commit])
        return completed_process.returncode == 0

    def contains(self, revision):
        return self.is_ancestor(revision, self.revision())

    def is_dirty(self):
        completed_process = self.git_run(['diff', '--quiet', 'HEAD'])
        return completed_process.returncode != 0

    def revision_of(self, branch_name):
        return self.git(['rev-parse', branch_name])

    def branch(self):
        branch = self.git(['rev-parse', '--symbolic-full-name', '--abbrev-ref', 'HEAD'])
        if branch == 'HEAD':
            return None
        else:
            return branch

    def sequence_in_branch(self):
        """
        Return the sequence number in the branch.
        Note that this number is unique only within a certain branch.
        :return: The number of commits from HEAD until the first commit of the repository.
        """
        sequence_in_branch_string = self.git(['rev-list', '--count', '--first-parent', 'HEAD'])
        return int(sequence_in_branch_string)

    def current_branches(self):
        return self.local_branches_of(self.revision())

    def local_branches_of(self, hash):
        branches = self.git(['branch', '--format="%(refname)"', '--points-at', hash]).split('\n')
        result = [branch[12:-1] for branch in branches if branch.startswith('"refs/heads/')]
        return result

    def upstream_branch(self):
        completed_process = self.git_run(['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'])
        if completed_process.returncode == 0:
            return self.decode_stdout(completed_process)
        else:
            return None

    def local_branches(self):
        local_branches = self.git(['branch', '--list', '--format="%(refname)"']).split('\n')
        result = [branch[12:-1] for branch in local_branches if branch.startswith('"refs/heads/')]
        return result

    def full_remote_branches(self):
        remote_branches = self.git(['branch', '--list', '--remotes', '--format="%(refname)"']).split('\n')
        result = [branch for branch in remote_branches if branch != 'refs/remotes/origin/HEAD']
        return result

    def full_remote_branch_of(self, branch_name):
        return 'refs/remotes/origin/' + branch_name

    def remote_branches(self):
        result = [branch[21:-1] for branch in self.full_remote_branches()]
        return result

    def remote_branches_containing(self, commit):
        dictionary = {branch:self.revision_of(self.full_remote_branch_of(branch)) for branch in self.remote_branches()}
        return {branch: revision for branch, revision in dictionary if self.is_ancestor(commit, revision)}

    def most_stable_remote_branch_containing(self, commit):
        """
        Return the short name of the most stable branch that contains the given commit
        and its revision.
        """
        dictionary = self.remote_branches_containing(commit)

        most_stable_branch = None
        most_stable_revision = None
        for branch, revision in dictionary:
            if not most_stable_revision or self.is_ancestor(most_stable_revision, revision):
                most_stable_revision = revision
                most_stable_branch = branch
        return most_stable_branch, most_stable_revision

    def remotes(self):
        """
        Return the remotes.
        """
        remotes = self.git(['remote']).split('\n')
        result = [remote for remote in remotes if remote and len(remote) > 0]
        return result

    def has_remote(self):
        return len(self.remotes()) > 0

    def create_branch(self, name):
        self.git(['checkout', '-b', name])

    def checkout_branch(self, name):
        self.git(['checkout', name])

    def force_create_branch(self, name, revision):
        """
        Force create a branch with the given name at the given revision.
        Set the upstream if there is a matching branch.
        """
        self.get(['branch', '-f', '-b', name, revision])
        self.checkout_branch(name)
        if name in self.remote_branches():
            self.set_upstream()

    def push(self):
        if self.upstream_branch():
            self.git(['push'])
        else:
            self.set_upstream()
            self.git(['push'])

    def set_upstream(self):
        self.git(['branch', '--set-upstream', 'origin', self.branch()])

    def checkout(self, revision):
        self.git(['checkout', revision])

    def fetch(self):
        self.git(['fetch'])

