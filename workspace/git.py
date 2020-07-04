import subprocess

class Git:
    def __init__(self, directory):
        self.directory = directory

    def add(self, file):
        return subprocess.run(['git', 'add', file], stdout=subprocess.PIPE, cwd=self.directory).stdout

    def commit(self, message):
        subprocess.run(['git', 'commit', '-m', message], stdout=subprocess.PIPE, cwd=self.directory).stdout

    def revision(self):
        hash = subprocess.run(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE, cwd=self.directory).stdout.rstrip().decode('utf-8')
        return hash

    def branch(self):
        branch = subprocess.run(['git', 'rev-parse', '--symbolic-full-name', '--abbrev-ref', 'HEAD'], stdout=subprocess.PIPE, cwd=self.directory)\
            .stdout.rstrip().decode('utf-8')
        if (branch == 'HEAD'):
            return None
        else:
            return branch

    def local_branches(self):
        branches = subprocess.run(['git', 'branch', '--list', '--format="%(refname)"'], stdout=subprocess.PIPE, cwd=self.directory)\
            .stdout.rstrip().decode('utf-8')
        all = branches.split('\n')
        result = [branch[1:-1] for branch in all if branch.startswith('"ref')]
        return result