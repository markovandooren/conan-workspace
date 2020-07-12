from tkinter import *
import tkinter.ttk
from tkinter import font
from tkinter import messagebox
from tkinter import simpledialog
from workspace.contract import *
from workspace.workspace import *
from workspace.tooltip import *
import threading
import subprocess

# Because of a bug in TkInter, getting the default background does not work on Windows.
# It cannot resolve the color SystemButtonFace.
default_background_color = 'gray85'

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
        self.editable_widget = None
        self.editable_var = BooleanVar(False)

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

        self.actual_revision_widget = Text(self.window, font=self.ui.revision_font, relief='flat',  width=41, height=1, borderwidth=0, bg=default_background_color)
        self.actual_revision_widget.grid(column=2, row=self.row, sticky=W)

        self.editable_widget = Button(self.window, image=self.ui.off_image, state=DISABLED)
        self.editable_widget.grid(column=3, row=self.row, sticky=W)

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
        self.branch_widget.grid(column=1, row=self.row, sticky=W)

    def refresh(self):
        package = self.workspace.package(self.name)

        self.name_widget.config(text=package.name)

        is_downloaded = package.is_downloaded()
        if self.is_downloaded != is_downloaded:
            self.is_downloaded = is_downloaded
            self.create_branch_widget()

        revision_font = self.ui.revision_font

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
                self.revision_tooltip = ToolTip(self.actual_revision_widget, 'The current revision is no descendant of the main revision\n' + main_revision)

            if package.git.is_dirty():
                revision_font = self.ui.revision_font_dirty
        else:
            branch_text = 'Download'
            branch_color = 'grey'
            actual_revision = package.main_revision()
            revision_color = 'gray'
        self.branch_widget.config(text=branch_text, fg=branch_color)
        self.actual_revision_widget.config(font=revision_font)
        self.actual_revision_widget.insert(1.0, actual_revision)
        self.actual_revision_widget.config(state=DISABLED, fg = revision_color, selectforeground = revision_color)

        editable = package.is_editable()
        self.editable_widget.config(image=self.ui.on_image if editable else self.ui.off_image)

    def destroy(self):
        if self.name_widget: self.name_widget.destroy()
        if self.branch_widget: self.branch_widget.destroy()
        if self.actual_revision_widget: self.actual_revision_widget.destroy()
        if self.branch_popup: self.branch_popup.destroy()
        if self.revision_tooltip: self.revision_tooltip.destroy()
        if self.editable_widget: self.editable_widget.destroy()

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
        self.on_image = tk.PhotoImage(width=48, height=24)
        self.off_image = tk.PhotoImage(width=48, height=24)
        self.on_image.put(default_background_color, to=(0, 0, 47, 23))
        self.on_image.put(("green",), to=(0, 0, 23, 23))
        self.off_image.put(default_background_color, to=(0, 0, 47, 23))
        self.off_image.put(("red",), to=(24, 0, 47, 23))
        self.window.resizable(width=False, height=False)
        self.refresh_button = None
        self.peg_button = None
        self.fetch_button = None

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
        self.revision_font_dirty = font.Font(family='Courier', weight=font.BOLD, slant=font.ITALIC, size=12)
        row = 0
        Label(self.window, text='Name ', font=self.name_font).grid(column=0, row=row, sticky=W)
        Label(self.window, text='Branch ', font=self.name_font).grid(column=1, row=row, sticky=W)
        Label(self.window, text='Revision ', font=self.name_font).grid(column=2, row=row, sticky=W)
        row = row + 1
        separator = tkinter.ttk.Separator(self.window, orient=HORIZONTAL)
        separator.grid(row=row, columnspan=4, sticky='WE')

    def disable_mutations(self):
        self.refresh_button.config(state=DISABLED)
        self.peg_button.config(state=DISABLED)

    def enable_mutations(self):
        self.refresh_button.config(state=NORMAL)
        self.peg_button.config(state=NORMAL)

    def run_async(self, task):
        def execute():
            self.disable_mutations()
            task()
            self.enable_mutations()

        t = threading.Thread(target=execute)
        t.start()

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
                self.run_async(self.refresh)

            def peg():
                try:
                    dirty_packages = [package.name for package in self.workspace.packages() if package.git.is_dirty()]
                    commit_message = None
                    if len(dirty_packages) > 0:
                        commit_message = simpledialog.askstring('Commit message', 'Packages ' + ', '.join(dirty_packages) + ' are dirty. Enter a commit message.')

                    self.workspace.peg(commit_message)
                except Exception as error:
                    messagebox.showerror('Workspace Error', error, icon='warning')
                finally:
                    self.refresh()

            def fetch():
                self.workspace.fetch()

            self.status_frame = Frame(self.window)
            self.status_frame.grid(row=row, column=0, columnspan=4, stick ='EW')
            self.refresh_button = Button(self.status_frame,text="Refresh", command=refresh)
            self.refresh_button.pack(side=tkinter.RIGHT)
            self.peg_button = Button(self.status_frame,text="Peg", command=peg)
            self.peg_button.pack(side=tkinter.RIGHT)
            self.fetch_button = Button(self.status_frame,text="Fetch", command=fetch)
            self.fetch_button.pack(side=tkinter.RIGHT)
            #row = row + 1

    def refreshable(self, widget):
        self.refreshable_widgets.append(widget)
        return widget