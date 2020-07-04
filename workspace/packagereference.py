import re

class PackageReference:

    @classmethod
    def from_string(self, reference_string):
        name_match = re.search('([^@]+)/', reference_string)
        name = name_match.group(1)

        revision_match = re.search('/([^@]*)\.([a-z0-9]*)', reference_string)
        semantic_version = revision_match.group(1)
        revision = revision_match.group(2)

        user_match = re.search('@([a-zA-Z]*)', reference_string)
        user = user_match.group(1) if user_match else None

        channel_match = re.search('@[a-zA-Z]*/([a-zA-Z]*)', reference_string)
        channel = channel_match.group(1) if channel_match else None
        return PackageReference(name, semantic_version, revision, user, channel)

    def __init__(self, name, semantic_version, revision, user, channel):
        self._name = name
        self._semantic_version = semantic_version
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
    def revision(self):
        return self._revision

    @property
    def user(self):
        return self._user

    @property
    def channel(self):
        return self._channel

    def to_string(self) -> str:
        result = self.name + '/' +self.semantic_version + '.' +  self.revision
        if (self.user):
            result = result + '@' + self.user + "/" + self.channel
        return result

    def clone(self):
        return PackageReference(self.name, self.semantic_version, self.revision, self.user, self.channel)

