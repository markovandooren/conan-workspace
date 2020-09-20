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

        def toggle_editable():
            self.package.toggle_editable()
            self.refresh_editable()

        self.editable_widget = Button(self.window, image=self.ui.off_image, command=toggle_editable)
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
        package = self.package

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
            tooltip = ''
            if main_revision == actual_revision:
                revision_color = 'green'
                tooltip = f'The current revision is equal to main revision\n' + main_revision
            elif package.has_valid_revision():
                revision_color = 'blue'
                tooltip = f'The current revision is ahead of the main revision\n' + main_revision
            else:
                revision_color = 'red'
                tooltip = 'The current revision is no descendant of the main revision\n' + main_revision

            if package.git.is_dirty():
                revision_font = self.ui.revision_font_dirty
                tooltip = tooltip + '\n' + 'The package has local changes.'
            self.revision_tooltip = ToolTip(self.actual_revision_widget, tooltip)
        else:
            branch_text = 'Download'
            branch_color = 'grey'
            actual_revision = package.main_revision()
            revision_color = 'gray'
        self.branch_widget.config(text=branch_text, fg=branch_color)
        self.actual_revision_widget.config(state=NORMAL, font=revision_font)
        self.actual_revision_widget.delete(1.0, END)
        self.actual_revision_widget.insert(1.0, actual_revision)
        self.actual_revision_widget.config(state=DISABLED, fg = revision_color, selectforeground = revision_color)

        self.refresh_editable()


    def refresh_editable(self):
        editable = self.package.is_editable()
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

        self.mutate_widgets = []
        self.refreshable_widgets = []
        self.package_views=[]
        self.number_of_packages = 0
        self.on_image = tk.PhotoImage(width=48, height=24)
        self.off_image = tk.PhotoImage(width=48, height=24)
        self.on_image.put(default_background_color, to=(0, 0, 47, 23))
        self.on_image.put(("green",), to=(0, 0, 23, 23))
        self.off_image.put(default_background_color, to=(0, 0, 47, 23))
        self.off_image.put(("red",), to=(24, 0, 47, 23))
        self.window.resizable(width=False, height=False)
        self.is_processing = False
        self.create_header()
        self.create_footer()

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
        Label(self.window, text='Edit ', font=self.name_font).grid(column=3, row=row, sticky=W)
        row = row + 1
        separator = tkinter.ttk.Separator(self.window, orient=HORIZONTAL)
        separator.grid(row=row, columnspan=4, sticky='WE')

    def create_footer(self):
        def refresh():
            self.run_async(self.refresh)

        def peg():
            try:
                dirty_package_names = [package.name for package in self.workspace.packages() if package.git.is_dirty()]
                commit_message = None
                if len(dirty_package_names) > 0:
                    commit_message = simpledialog.askstring('Commit message', 'Packages ' + ', '.join(
                        dirty_package_names) + ' are dirty. Enter a commit message.')

                self.workspace.peg(commit_message)
            except Exception as error:
                messagebox.showerror('Workspace Error', error, icon='warning')
            finally:
                self.refresh()

        def create_branch():
            try:
                branch_name = simpledialog.askstring('Branch', 'Enter the branch name.')
                self.workspace.create_branch(branch_name)
            except Exception as error:
                messagebox.showerror('Workspace Error', error, icon='warning')
            finally:
                self.refresh()

        def fetch():
            self.run_async(self.workspace.fetch)

        def push():
            package_names_without_remotes = [package.name for package in self.workspace.editable_packages() if not package.git.has_remote()]
            do_push = True
            if len(package_names_without_remotes) > 0:
                do_push = messagebox.askokcancel('Push', 'Packages %s have no remote set. Continue with push?' % ', '.join(package_names_without_remotes), icon='warning')
            if do_push:
                self.run_async(self.workspace.push)

        self.status_frame = Frame(self.window)
        self.add_button(Button(self.status_frame, text="Refresh", command=refresh))
        self.add_button(Button(self.status_frame, text="Peg", command=peg))
        self.add_button(Button(self.status_frame, text="Fetch", command=fetch))
        self.add_button(Button(self.status_frame, text="Push", command=push))
        self.add_button(Button(self.status_frame, text="Branch", command=create_branch))

    def add_button(self, button):
        button.pack(side=tkinter.RIGHT)
        self.mutate_widgets.append(button)

    def disable_mutations(self):
        for widget in self.mutate_widgets:
            widget.config(state=DISABLED)

    def enable_mutations(self):
        for widget in self.mutate_widgets:
            widget.config(state=NORMAL)

    def run_async(self, task):
        if not self.is_processing:
            self.is_processing = True
            def execute():
                task()
                self.is_processing = False

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
            self.status_frame.grid(row=row, column=0, columnspan=4, stick ='EW')


    def refreshable(self, widget):
        self.refreshable_widgets.append(widget)
        return widget