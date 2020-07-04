import subprocess

class Editable:
    def __init__(self, package_reference, path, layout):
        self.package_reference = package_reference
        self.path = path
        self.layout = layout

    def disable(self):
        subprocess.run(['conan', 'editable', 'remove', self.package_reference.to_string()])

    def edit(self):
        ref = self.package_reference
        subprocess.run(['conan', 'editable', 'add', self.path, ref.to_string()])

