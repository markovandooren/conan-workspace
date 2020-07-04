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
        self.name = name
        self.semantic_version = semantic_version
        self.revision = revision
        self.user = user
        self.channel = channel

    def to_string(self) -> str:
        result = self.name + '/' +self.semantic_version + '.' +  self.revision
        if (self.user):
            result = result + '@' + self.user + "/" + self.channel
        return result

    def clone(self):
        return PackageReference(self.name, self.semantic_version, self.revision, self.user, self.channel)

