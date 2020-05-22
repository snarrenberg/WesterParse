from music21 import *

class DependencyException(exceptions21.Music21Exception):
    pass

class Dependency():
    '''An object for storing the dependencies of a Note in a Lyne'''
    validDirections = ('ascending', 'descending', None)

    def __init__(self, *args, **keywords):
        '''Object for storing the dependencies of a Note in a Lyne'''        
        # dependencies default to None
        self._lefthead = None  # can be a single lyne element -- note.index
        self._righthead = None  # can be a single lyne element -- note.index
        # self.heads = [lefthead, righthead] either may be None, 
        # L = self.heads[0], R= self.heads[1]
        self._left = None  # a single Note [index?]
        self._right = None  # a single Note [index?] (or none for repetitions)
        self._approach = None # must be ascending or descending or None
        self._departure = None # must be ascending or descending or None
        self._dependents = [] # can be one or more Note.indexes
        # dependents should be a list of lists, one for each structure
        # should there be separate categories for left-dependents and right-dependents?
        # should multiple passing tones be codependent?
            # codependents could be calculated from differences between left and lefthead
            # and right and righthead
#        self.level
        
    def gatherAttrs(self):
        attrs = []
        if self.lefthead != None:
#            attrs.append('lefthead: %s' % self.lefthead.nameWithOctave)
#        else:
            attrs.append('lefthead: %s' % str(self.lefthead))

        if self.righthead != None:
#            attrs.append('righthead: %s' % self.righthead.nameWithOctave)
#        else:
            attrs.append('righthead: %s' % str(self.righthead))

        if self.left != None:
#            attrs.append('left: %s' % self.left.nameWithOctave)
#        else:
            attrs.append('left: %s' % str(self.left))

        if self.right != None:
#            attrs.append('right: %s' % self.right.nameWithOctave)
#        else:
            attrs.append('right: %s' % str(self.right))

        if self.approach != None:
            attrs.append('approach: %s' % self.approach)
        else:
            attrs.append('approach: %s' % self.approach)

        if self.departure != None:
            attrs.append('departure: %s' % self.departure)
        else:
            attrs.append('departure: %s' % self.departure)

        if len(self.dependents) == 0:
            attrs.append('dependents: %s' % str(None))
        else:
            deps = []
            for n in self.dependents:
#                deps.append(n.nameWithOctave)
                deps.append(n)
            attrs.append('dependents: %s' % deps)
        return '\n\t'.join(attrs)
        
    def __repr__(self):
        # TODO set this up as a dictionary, with attribute names as keys
        return '[%s: %s]' % (self.__class__.__name__, self.gatherAttrs())
#         rep = []
#         deps = []
#         for n in [self.lefthead, self.righthead, self.left, self.right]:
#             if n != None:
#                 rep.append(n.nameWithOctave)
#             else:
#                 rep.append(n)
#         if len(self.dependents) == 0:
#             deps.append(None)
#         else:
#             for n in self.dependents:
#                 deps.append(n.nameWithOctave)
#         rep.append('%s' % deps)
#         rep.append(self.approach)
#         return(str(rep))

    @property
    def lefthead(self):
        return self._lefthead
    @lefthead.setter
    def lefthead(self, n):
        if n != None:
            try:
                isinstance(n, int)
                #n.isClassOrSubclass((note.Note,))
            except:
                raise DependencyException('not a valid dependency object: %s' % n)
        self._lefthead = n

    @property
    def righthead(self):
        return self._righthead
    @righthead.setter
    def righthead(self, n):
        if n != None:
            try:
                isinstance(n, int)
                #n.isClassOrSubclass((note.Note,))
            except:
                raise DependencyException('not a valid dependency object: %s' % n)
        self._righthead = n

    @property
    def left(self):
        return self._left
    @left.setter
    def left(self, n):
        if n != None:
            try:
                isinstance(n, int)
                #n.isClassOrSubclass((note.Note,))
            except:
                raise DependencyException('not a valid dependency object: %s' % n)
        self._left = n

    @property
    def right(self):
        return self._right
    @right.setter
    def right(self, n):
        if n != None:
            try:
                isinstance(n, int)
                #n.isClassOrSubclass((note.Note,))
            except:
                raise DependencyException('not a valid dependency object: %s' % n)
        self._right = n

    @property
    def approach(self):
        return self._approach
    @approach.setter
    def approach(self, d):
        if d not in self.validDirections:
            raise LyneException('not a valid direction: %s' % d)
        self._approach = d

    @property
    def departure(self):
        return self._departure
    @approach.setter
    def departure(self, d):
        if d not in self.validDirections:
            raise LyneException('not a valid direction: %s' % d)
        self._departure = d

    @property
    def dependents(self):
        return self._dependents
    @dependents.setter
    def dependents(self, n):
        if n != []:
            try:
                n.isClassOrSubclass((note.Note,))
            except:
                raise DependencyException('not a valid dependency object: %s' % n)
        self._dependents = n

if __name__ == "__main__":
    # self_test code
    pass