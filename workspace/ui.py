from tkinter import *
import tkinter.ttk
from tkinter import font
from workspace.contract import *
from workspace.workspace import *
from workspace.tooltip import *
import subprocess

class PackageView:
    def __init__(self, ui, name, row):
        self.ui = ui
        self.name = name
        self.row = row
        self.label = None
        self.name_widget = None
        self.branch_widget = None
        self.actual_revision_widget = None
        self.is_downloaded = False
        self.branch_popup = None
        self.revision_tooltip = None

    @property
    def workspace(self):
        return self.ui.workspace

    @property
    def window(self):
        return self.ui.window

    @property
    def name_font(self):
        return self.ui.name_font

    @property
    def package(self):
        return self.workspace.package(self.name)

    def create(self):
        self.name_widget = Label(self.window, font=self.name_font)
        self.name_widget.grid(column=0, row=self.row, sticky=W)

        self.create_branch_widget()

        self.actual_revision_widget = Label(self.window, font=self.ui.revision_font)
        self.actual_revision_widget.grid(column=2, row=self.row, sticky=W)
        self.refresh()

    def create_branch_widget(self):
        if self.branch_widget:
            self.branch_widget.destroy()

        if self.is_downloaded:
            self.branch_widget = Label(self.window, font=self.name_font, justify=LEFT)
            self.branch_popup = Menu(self.branch_widget, tearoff=0, title=self.name)
            def do_popup(event):
                # display the popup menu
                self.branch_popup.delete(0, 'end')

                def run_gitk():
                    subprocess.Popen('gitk', cwd=self.package.directory())

                def run_git_gui():
                    subprocess.Popen(['git', 'gui'], cwd=self.package.directory())

                self.branch_popup.add_command(label=self.name, state=tkinter.DISABLED)  # , command=next) etc...
                self.branch_popup.add_command(label="Git History", command=run_gitk)  # , command=next) etc...
                self.branch_popup.add_command(label="Git Commit", command=run_git_gui)

                self.branch_popup.tk_popup(event.x_root, event.y_root, 0)
            self.branch_widget.bind("<Button-3>", do_popup)

        else:
            def download():
                self.workspace.download(self.name)
                self.refresh()
            self.branch_widget = Button(self.window, font=self.name_font, justify=LEFT, command=download)
        self.branch_widget.grid(column=1, row=self.row, sticky=EW)

    def refresh(self):
        package = self.workspace.package(self.name)

        self.name_widget.config(text=package.name)

        is_downloaded = package.is_downloaded()
        if self.is_downloaded != is_downloaded:
            self.is_downloaded = is_downloaded
            self.create_branch_widget()

        if is_downloaded:
            branch = package.git.branch()
            branch_text = branch + ' ' if branch else 'no branch '
            branch_color = 'black' if branch else 'red'

            main_revision = package.main_revision()
            actual_revision = package.git.revision()
            if main_revision == actual_revision:
                revision_color = 'green'
            elif package.has_valid_revision():
                revision_color = 'blue'
            else:
                revision_color = 'red'
                self.revision_tooltip = ToolTip(self.actual_revision_widget, 'The current revision is no descendant of main revision\n' + main_revision)
        else:
            branch_text = 'Download'
            branch_color = 'grey'
            actual_revision = ''
            revision_color = 'gray'
        self.branch_widget.config(text=branch_text, fg=branch_color)
        self.actual_revision_widget.config(text=actual_revision, fg = revision_color)

    def destroy(self):
        if self.name_widget: self.name_widget.destroy()
        if self.branch_widget: self.branch_widget.destroy()
        if self.actual_revision_widget: self.actual_revision_widget.destroy()
        if self.branch_popup: self.branch_popup.destroy()
        if self.revision_tooltip: self.revision_tooltip.destroy()

class UI:
    def __init__(self, workspace):
        require(workspace)
        self._workspace = workspace
        self.window = Tk()
        self.create_header()
        self.refreshable_widgets = []
        self.package_views=[]
        self.number_of_packages = 0
        self.status_frame = None

    @property
    def workspace(self):
        return self._workspace

    def run(self):
        self.window.title("Feature Branch Workspace")
        self.refresh()
        self.window.mainloop()

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
        number_of_packages = self.workspace.graph.number_of_nodes()
        if number_of_packages == self.number_of_packages:
            for package_view in self.package_views:
                package_view.refresh()
        else:
            for package_view in self.package_views:
                package_view.destroy()
                self.status_frame.destroy()
            self.package_views = []
            package_names = self.workspace.package_name_order()
            self.number_of_packages = len(package_names)
            row = 2
            for package_name in package_names:
                package_view = PackageView(self, package_name, row)
                self.package_views.append(package_view)
                package_view.create()
                row = row + 1

            separator = tkinter.ttk.Separator(self.window, orient=HORIZONTAL)
            separator.grid(row=row, columnspan=3, sticky='WE')
            row = row + 1
            def refresh():
                self.refresh()

            def peg():
                self.workspace.peg()
                self.refresh()

            self.status_frame = Frame(self.window)
            self.status_frame.grid(row=row, column=0, columnspan=3, stick ='EW')
            refresh_button = Button(self.status_frame,text="Refresh", command=refresh)
            refresh_button.pack(side=tkinter.RIGHT)
            peg_button = Button(self.status_frame,text="Peg", command=peg)
            peg_button.pack(side=tkinter.RIGHT)

    def refreshable(self, widget):
        self.refreshable_widgets.append(widget)
        return widget