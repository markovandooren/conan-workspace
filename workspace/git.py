import subprocess

class Git:
    def __init__(self, directory):
        self.directory = directory

    def git(self, args):
        return subprocess.run(['git'] + args, stdout=subprocess.PIPE, cwd=self.directory).stdout.rstrip().decode('utf-8')

    def add(self, file):
        return self.git(['add', file])

    def commit(self, message):
        self.git(['commit', '-m', message])

    def push(self):
        self.git(['push'])

    def revision(self):
        return self.git(['rev-parse', 'HEAD'])

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

    def local_branches(self):
        branches = self.git(['branch', '--list', '--format="%(refname)"'])
        all = branches.split('\n')
        result = [branch[1:-1] for branch in all if branch.startswith('"ref')]
        return result