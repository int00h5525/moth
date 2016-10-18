#!/usr/bin/python3

import argparse
from collections import defaultdict, namedtuple
import glob
import hashlib
from importlib.machinery import SourceFileLoader
import mistune
import os
import random
import tempfile

messageChars = b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

def djb2hash(buf):
    h = 5381
    for c in buf:
        h = ((h * 33) + c) & 0xffffffff
    return h

# We use a named tuple rather than a full class, because any random name generation has
# to be done with Puzzle's random number generator, and it's cleaner to not pass that around.
PuzzleFile = namedtuple('PuzzleFile', ['path', 'handle', 'name', 'visible'])


class Puzzle:

    KNOWN_KEYS = [
        'answer',
        'author',
        'file',
        'hidden',
        'name'
        'resource',
        'summary'
    ]
    REQUIRED_KEYS = [
        'author',
        'answer',
        'points'
    ]
    SINGULAR_KEYS = [
        'name'
    ]

    # Get a big list of clean words for our answer file.
    ANSWER_WORDS = [w.strip() for w in open(os.path.join(os.path.dirname(__file__),
                                                         'answer_words.txt'))]

    def __init__(self, path, category_seed):
        """Puzzle objects need a path to a puzzle description (
        :param path:
        :param category_seed:
        """

        super().__init__()

        if not os.path.isdir(path):
            raise ValueError("No such directory: {}".format(path))

        self._dict = defaultdict(lambda: [])
        if os.path.isdir(path):
            self._puzzle_dir = path
        else:
            self._puzzle_dir = None
        self.message = bytes(random.choice(messageChars) for i in range(20))
        self.body = ''

        # A list of temporary files we've created that will need to be deleted.
        self._temp_files = []

        # Expected format is path/<points_int>.moth
        pathname = os.path.split(path)[-1]
        try:
            self.points = int(pathname)
        except ValueError:
            raise ValueError("Directory name must be a point value: {}".format(path))
        files = os.listdir(path)

        self._seed = category_seed * self.points
        self.rand = random.Random(self._seed)

        if 'puzzle.moth' in files:
            self._read_config(open(os.path.join(path, 'puzzle.moth')))

        if 'puzzle.py' in files:
            # Good Lord this is dangerous as fuck.
            loader = SourceFileLoader('puzzle_mod', os.path.join(path, 'puzzle.py'))
            puzzle_mod = loader.load_module()
            if hasattr(puzzle_mod, 'make'):
                self.body = '# `puzzle.body` was not set by the `make` function'
                puzzle_mod.make(self)
            else:
                self.body = '# `puzzle.py` does not define a `make` function'

    def cleanup(self):
        """Cleanup any outstanding temporary files."""
        for path in self._temp_files:
            if os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass

    def _read_config(self, stream):
        """Read a configuration file (ISO 2822)"""
        body = []
        header = True
        for line in stream:
            if header:
                line = line.strip()
                if not line.strip():
                    header = False
                    continue
                key, val = line.split(':', 1)
                val = val.strip()
                self[key] = val
            else:
                body.append(line)
        self.body = ''.join(body)

    def random_hash(self):
        """Create a random hash from our number generator suitable for use as a filename."""
        return hashlib.sha1(str(self.rand.random()).encode('ascii')).digest()

    def _puzzle_file(self, path, name, visible=True):
        """Make a puzzle file instance for the given file. To add files as you would in the config
        file (to 'file', 'hidden', or 'resource', simply assign to that keyword in the object:
          puzzle['file'] = 'some_file.txt'
          puzzle['hidden'] = 'some_hidden_file.txt'
          puzzle['resource'] = 'some_file_in_the_category_resource_directory_omg_long_name.txt'
        :param path: The path to the file
        :param name: The name of the file. If set to None, the published file will have
                     a random hash as a name and have visible set to False.
        :return:
        """

        # Make sure it actually exists.
        if not os.path.exists(path):
            raise ValueError("Included file {} does not exist.")

        file = open(path, 'rb')

        return PuzzleFile(path=path, handle=file, name=name, visible=visible)

    def make_temp_file(self, name=None, mode='rw+b', visible=True):
        """Get a file object for adding dynamically generated data to the puzzle. When you're
        done with this file, flush it, but don't close it.
        :param name: The name of the file for links within the puzzle. If this is None, a name
                     will be generated for you.
        :param mode: The mode under which
        :param visible: Whether or not the file will be visible to the user.
        :return: A file object for writing
        """

        if name is None:
            name = self.random_hash()

        file = tempfile.NamedTemporaryFile(mode=mode, delete=False)
        file_read = open(file.name, 'rb')

        self._dict['files'][name] = PuzzleFile(path=file.name, handle=file_read,
                                               name=name, visible=visible)

        return file

    def make_handle_file(self, handle, name, visible=True):
        """Add a file to the puzzle from a file handle.
        :param handle: A file object or equivalent.
        :param name: The name of the file in the final puzzle.
        :param visible: Whether or not it's visible.
        :return: None
        """

    def __setitem__(self, key, value):
        """Set a value for this puzzle, as if it were set in the config file. Most values default
        being added to a list. Files (regardless of type) go in a dict under ['files']. Keys
        in Puzzle.SINGULAR_KEYS are single values that get overwritten with subsequent assignments.
        Only keys in Puzzle.KNOWN_KEYS are accepted.
        :param key:
        :param value:
        :return:
        """

        key = key.lower()

        if key in ('file', 'resource', 'hidden') and self._puzzle_dir is None:
            raise KeyError("Cannot set a puzzle file for single file puzzles.")

        if key == 'answer':
            # Handle adding answers to the puzzle
            self._dict['hashes'].append(djb2hash(value.encode('utf8')))
            self._dict['answers'].append(value)
        elif key == 'file':
            # Handle adding files to the puzzle
            path = os.path.join(self._puzzle_dir, 'files', value)
            self._dict['files'][value] = self._puzzle_file(path, value)
        elif key == 'resource':
            # Handle adding category files to the puzzle
            path = os.path.join(self._puzzle_dir, '../res', value)
            self._dict['files'].append(self._puzzle_file(path, value))
        elif key == 'hidden':
            # Handle adding secret, 'hidden' files to the puzzle.
            path = os.path.join(self._puzzle_dir, 'files', value)
            name = self.random_hash()
            self._dict['files'].append(self._puzzle_file(path, name, visible=False))
        elif key in self.SINGULAR_KEYS:
            # These keys can only have one value
            self._dict[key] = value
        elif key in self.KNOWN_KEYS:
            self._dict[key].append(value)
        else:
            raise KeyError("Invalid Attribute: {}".format(key))

    def __getitem__(self, item):
        return self._dict[item.lower()]

    def make_answer(self, word_count, sep=' '):
        """Generate and return a new answer. It's automatically added to the puzzle answer list.
        :param int word_count: The number of words to include in the answer.
        :param str|bytes sep: The word separator.
        :returns: The answer string
        """

        answer = sep.join(self.rand.sample(self.ANSWER_WORDS, word_count))
        self['answer'] = answer

        return answer

    def htmlify(self):
        """Format and return the markdown for the puzzle body."""
        return mistune.markdown(self.body)

    def publish(self):
        obj = {
            'author': self['author'],
            'hashes': self['hashes'],
            'body': self.htmlify(),
        }
        return obj

    def secrets(self):
        obj = {
            'answers': self['answers'],
            'summary': self['summary'],
        }
        return obj

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build a puzzle category')
    parser.add_argument('puzzledir', nargs='+', help='Directory of puzzle source')
    args = parser.parse_args()

    for puzzledir in args.puzzledir:
        puzzles = {}
        secrets = {}
        for puzzlePath in glob.glob(os.path.join(puzzledir, "*.moth")):
            filename = os.path.basename(puzzlePath)
            points, ext = os.path.splitext(filename)
            points = int(points)
            puzzle = Puzzle(puzzlePath, "test")
            puzzles[points] = puzzle

        for points in sorted(puzzles):
            puzzle = puzzles[points]
            print(puzzle.secrets())


class Category:
    def __init__(self, path, seed):
        self.path = path
        self.seed = seed
        self.pointvals = []
        for fpath in glob.glob(os.path.join(path, "[0-9]*")):
            pn = os.path.basename(fpath)
            points = int(pn)
            self.pointvals.append(points)
        self.pointvals.sort()

    def puzzle(self, points):
        path = os.path.join(self.path, str(points))
        return Puzzle(path, self.seed)

    def puzzles(self):
        for points in self.pointvals:
            yield self.puzzle(points)
