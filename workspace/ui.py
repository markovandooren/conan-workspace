from tkinter import *
from tkinter import font
from workspace.contract import *
from workspace.workspace import *

class UI:
    def __init__(self, workspace):
        require(workspace)
        self._workspace = workspace

    @property
    def workspace(self):
        return self._workspace

    def run(self):
        window = Tk()
        window.title("Feature Branch Workspace")

        name_font = font.Font(family='Courier', size=12, weight=font.BOLD)
        revision_font = font.Font(family='Courier', weight=font.BOLD, size=12)

        longest_branch_name = max([ package.git.branch() for package in self.workspace.packages() if package.git.branch()], key=len)
        longest_branch_length = len(longest_branch_name)

        package_names = self.workspace.package_name_order()

        row = 0
        for package_name in package_names:
            package = self.workspace.package(package_name)
            name_label = Label(window, text=package_name + ' : ', font=name_font)
            name_label.grid(column=0, row=row)

            # main_revision_label = Label(window, text=package.main_revision(), font=font)
            # main_revision_label.grid(column=1, row=row)
            branch = package.git.branch()
            branch_text = branch if branch else ""
            branch_text = branch_text + (" " * (longest_branch_length + 1 - len(branch_text)))
            branch_label = Label(window, text=branch_text, font=name_font)
            branch_label.grid(column=1, row=row)

            main_revision = package.main_revision()
            actual_revision = package.git.revision()
            revision_color = "black" if main_revision == actual_revision else "red"
            actual_revision_label = Label(window, text=actual_revision, font=revision_font, fg=revision_color)
            actual_revision_label.grid(column=2, row=row)

            row = row + 1
        window.mainloop()
