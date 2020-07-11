from tkinter import *
import tkinter.ttk
from tkinter import font
from workspace.contract import *
from workspace.workspace import *

class PackageView:
    def __init__(self, ui, name, row):
        self.ui = ui
        self.name = name
        self.row = row
        self.label = None
        self.name_label = None
        self.branch_label = None
        self.actual_revision_label = None

    @property
    def workspace(self):
        return self.ui.workspace

    @property
    def window(self):
        return self.ui.window

    @property
    def name_font(self):
        return self.ui.name_font

    def create(self):
        package = self.workspace.package(self.name)
        self.name_label = Label(self.window, font=self.name_font)
        self.name_label.grid(column=0, row=self.row, sticky=W)

        self.branch_label = Label(self.window, font=self.name_font, justify=LEFT)
        self.branch_label.grid(column=1, row=self.row, sticky=W)

        self.actual_revision_label = Label(self.window, font=self.ui.revision_font)
        self.actual_revision_label.grid(column=2, row=self.row, sticky=W)
        self.refresh()

    def refresh(self):
        package = self.workspace.package(self.name)

        self.name_label.config(text=package.name)

        branch = package.git.branch()
        branch_text = branch + ' ' if branch else 'no branch '
        branch_color = 'black' if branch else 'red'
        self.branch_label.config(text=branch_text, fg=branch_color)

        main_revision = package.main_revision()
        actual_revision = package.git.revision()
        revision_color = 'green' if main_revision == actual_revision else 'blue'

        self.actual_revision_label.config(text=actual_revision, fg = revision_color)

    def destroy(self):
        self.label.destroy()

class UI:
    def __init__(self, workspace):
        require(workspace)
        self._workspace = workspace
        self.window = Tk()
        self.create_header()

    @property
    def workspace(self):
        return self._workspace

    def run(self):
        self.window.title("Feature Branch Workspace")
        self.refresh()
        self.window.mainloop()
        self.refreshable_widgets = []
        self.package_views=[]

    def create_header(self):
        self.name_font = font.Font(family='Courier', size=12, weight=font.BOLD)
        self.revision_font = font.Font(family='Courier', weight=font.BOLD, size=12)
        row = 0
        Label(self.window, text='Name ', font=self.name_font).grid(column=0, row=row, sticky=W)
        Label(self.window, text='Branch ', font=self.name_font).grid(column=1, row=row, sticky=W)
        Label(self.window, text='Revision ', font=self.name_font).grid(column=2, row=row, sticky=W)
        row = row + 1
        separator = tkinter.ttk.Separator(self.window, orient=HORIZONTAL)
        separator.grid(row=row, columnspan=3, sticky='WE')

    def refresh(self):
        self.workspace.update_graph()


        longest_branch_name = max([ package.git.branch() for package in self.workspace.packages() if package.git.branch()], key=len)
        longest_branch_length = len(longest_branch_name)

        package_names = self.workspace.package_name_order()
        row = 2
        for package_name in package_names:
            PackageView(self, package_name, row).create()
            row = row + 1



        separator = tkinter.ttk.Separator(self.window, orient=HORIZONTAL)
        separator.grid(row=row, columnspan=3, sticky='WE')
        row = row + 1
        def refresh():
            for widget in self.window.winfo_children():
                widget.destroy()
            self.refresh()
        Button(self.window,text="Refresh", command=refresh).grid(column=2, sticky=E, row=row)

    def refreshable(self, widget):
        self.refreshable_widgets.append(widget)
        return widget