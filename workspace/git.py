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

    def push(self):
        self.git(['push'])

    def revision(self):
        return self.revision_of('HEAD')

    def contains(self, revision):
        completed_process = self.git_run(['merge-base', '--is-ancestor', revision, self.revision()])
        return completed_process.returncode == 0

    def is_dirty(self):
        completed_process = self.git_run(['diff', '--quiet', 'HEAD'])
        return completed_process.returncode != 0

    def revision_of(self, branch_name):
        return self.git(['rev-parse', branch_name])

    def branch(self):
        branch = self.git(['rev-parse', '--symbolic-full-name', '--abbrev-ref', 'HEAD'])
        if (branch == 'HEAD'):
            return None
        else:
            return branch

    def sequence_in_branch(self):
        """
        Return the sequence number in the branch.
        Note that this number is unique only within a certain branch.
        :return: The number of commits from HEAD until the first commit of the repository.
        """
        sequence_in_branch_string = self.git(['rev-list', '--count', 'HEAD'])
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

    def remote_branches(self):
        remote_branches = self.git(['branch', '--list', '--remotes', '--format="%(refname)"']).split('\n')
        result = [branch[21:-1] for branch in remote_branches if branch != 'refs/remotes/origin/HEAD']
        return result

    def create_branch(self, name):
        self.git(['checkout', '-b', name])

    def checkout_branch(self, name):
        self.git(['checkout', name])

    def push(self):
        if self.upstream_branch():
            self.git(['push'])
        else:
            self.git(['branch', '--set-upstream', 'origin', self.branch()])

    def checkout(self, revision):
        self.git(['checkout', revision])

    def remotes(self):
        out = self.git(['remote'])
        remotes = out.split('\n') if len(out) > 0 else []
        return remotes

    def fetch(self):
        self.git(['fetch'])