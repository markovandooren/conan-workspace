import re
from workspace.contract import *


class PackageReference:
    """
    A Conan package reference that uses feature branches. In Conan files it is represented as:
    name/semantic_version.revision@user/channel
    """
    @classmethod
    def from_string(self, reference_string):
        require(reference_string)

        name_match = re.search('([^@]+)/', reference_string)
        name = name_match.group(1)

        revision_match = re.search('/([^@]*)\.([0-9]*)\.([a-z0-9]*)', reference_string)
        semantic_version = revision_match.group(1)
        sequence_in_branch = int(revision_match.group(2))
        revision = revision_match.group(3)

        user_match = re.search('@([a-zA-Z]*)', reference_string)
        user = user_match.group(1) if user_match else None

        channel_match = re.search('@[a-zA-Z]*/([a-zA-Z]*)', reference_string)
        channel = channel_match.group(1) if channel_match else None
        return PackageReference(name, semantic_version, sequence_in_branch, revision, user, channel)

    def __init__(self, name, semantic_version, sequence_in_branch, revision, user, channel):
        require(name)
        require(semantic_version)
        require(revision)
        require(sequence_in_branch >= 0)
        require(not user or len(user) > 1, 'Channel must have at least 2 characters.')
        require(not channel or len(channel) > 1, 'Channel must have at least 2 characters.')

        self._name = name
        self._semantic_version = semantic_version
        self._sequence_in_branch = sequence_in_branch
        self._revision = revision
        self._user = user
        self._channel = channel

    @property
    def name(self):
        return self._name

    @property
    def semantic_version(self):
        return self._semantic_version

    @property
    def sequence_in_branch(self):
        return self._sequence_in_branch

    @property
    def revision(self):
        return self._revision

    @property
    def user(self):
        return self._user

    @property
    def channel(self):
        return self._channel

    def to_string(self) -> str:
        result = self.name + '/' +self.semantic_version + '.' + str(self.sequence_in_branch) + '.' +  self.revision
        if (self.user):
            result = result + '@' + self.user + "/" + self.channel
        return result

    def clone(self, sequence_in_branch, revision):
        return PackageReference(self.name, self.semantic_version, sequence_in_branch, revision, self.user, self.channel)

