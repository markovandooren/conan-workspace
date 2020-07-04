import unittest

from workspace.packagereference import *

class PackageReferenceTest(unittest.TestCase):

    def test_from_string(self):
        # GIVEN Nothing
        ref = PackageReference("name", "1.2.3", "677c01bbb54ccba4307bf468cb907e3988fb2e19", "user", "test")
        self.assertEqual("name", ref.name)
        self.assertEqual("1.2.3", ref.semantic_version)
        self.assertEqual("677c01bbb54ccba4307bf468cb907e3988fb2e19", ref.revision)
        self.assertEqual("user", ref.user)
        self.assertEqual("test", ref.channel)

if __name__ == '__main__':
    unittest.main()
