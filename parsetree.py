#Regular Expression Implementation ,Written by Adrian Stoll
import re2 as re
from config import *
from enum import Enum

class Type(Enum):
    HOLE = 0
    CHAR = 1
    K = 2
    Q = 3
    C = 4
    U = 5
    EPS = 6
    REGEX = 10

def is_inclusive(superset, subset):
    # R -> R    sup-nohole sub-nohole
    if repr(superset) == repr(subset) and not superset.hasHole():
        return True
    # R -> (0+1)*   sup-nohole sub-hole
    if repr(superset) == '(0|1)*':
        return True
    # made of 0s -> 0*, made of 1s -> 1* - nohole
    if repr(superset) == '0*' and '1' not in repr(subset) and not subset.hasHole():
        return True
    if repr(superset) == '1*' and '0' not in repr(subset) and not subset.hasHole():
        return True
    # R -> R*, R -> R?, R? -> R* - nohole
    if (superset.type == Type.K or superset.type == Type.Q) and not superset.hasHole():
        if repr(superset.r) == repr(subset):
            return True
        elif subset.type == Type.Q and repr(superset.r) == repr(subset.r):
            return True
    # R -> (R + r)*     sub- no hole
    if superset.type == Type.K and superset.r.type == Type.U and not subset.hasHole():
        for index, regex in enumerate(superset.r.list):
            if is_inclusive(KleenStar(regex), subset):
                return True

class RE:
    def __lt__(self, other):
        return False

    def rpn(self):
        if self.type == Type.K or self.type == Type.Q:
            return self.r.rpn()+1
        elif self.type == Type.C or self.type == Type.U:
            return sum(list(i.rpn() for i in self.list)) + len(self.list) -1
        elif self.type == Type.REGEX:
            return self.r.rpn()
        else:
            return 1

    def spread(self, case):
        self.string = None

        if self.type == Type.K or self.type == Type.Q:
            if self.r.type == Type.HOLE:
                self.r = case
                return True
            else:
                return self.r.spread(case)

        elif self.type == Type.C:
            for index, regex in enumerate(self.list):
                if regex.type == Type.HOLE:
                    if case.type == Type.C:
                        self.list.append(Hole())
                        return True
                    else:
                        self.list[index] = case
                        return True
                elif regex.hasHole():
                    self.list[index].spread(case)
                    return True
            return False

        elif self.type == Type.U:
            for index, regex in enumerate(self.list):

                if regex.type == Type.HOLE:
                    if case.type == Type.U:
                        self.list.append(Hole())
                        self.list.sort(
                            key=lambda regex: '~' if repr(regex) == '#' else ('}' if regex.hasHole() else repr(regex)))
                        return True
                    else:
                        self.list[index] = case
                        self.list.sort(
                            key=lambda regex: '~' if repr(regex) == '#' else ('}' if regex.hasHole() else repr(regex)))
                        return True
                elif regex.hasHole():
                    self.list[index].spread(case)
                    self.list.sort(
                        key=lambda regex: '~' if repr(regex) == '#' else ('}' if regex.hasHole() else repr(regex)))
                    return True
            return False
        elif self.type == Type.REGEX:
            # 연속된 spread제어
            if case.type != Type.CHAR:
                if case.type == self.lastRE:
                    return False
                if self.lastRE == Type.K and case.type == Type.Q:
                    return False
                if self.lastRE == Type.Q and case.type == Type.K:
                    return False

            if repr(case) == '0|1':
                self.lastRE = Type.CHAR
            else:
                self.lastRE = case.type

            if self.r.type == Type.HOLE:
                self.r = case
                return True
            else:
                return self.r.spread(case)
        else:
            return False



    def prior_unroll(self):
        self.string = None

        if self.type == Type.C or self.type == Type.U:
            for index, regex in enumerate(self.list):
                if regex.type == Type.K and not regex.allHole():
                    s1 = regex.r
                    s2 = regex.r
                    s3 = regex
                    self.list[index] = Concatenate(s1, s2, s3)
                elif regex.type == Type.Q:
                    self.list[index] = self.list[index].r
                    self.list[index].prior_unroll()
                else:
                    self.list[index].prior_unroll()
        elif self.type == Type.REGEX:
            if self.r.type == Type.K and not self.r.allHole():
                s1 = self.r.r
                s2 = self.r.r
                s3 = self.r

                self.r= Concatenate(s1, s2, s3)
            elif self.r.type == Type.Q:
                self.r = self.r.r
                self.r.prior_unroll()
            else:
                self.r.prior_unroll()


    def starnormalform(self):
        if self.type == Type.K or self.type == Type.Q:
            if self.r.hasEps():
                return True
            else:
                return self.r.starnormalform()
        elif self.type == Type.C or self.type == Type.U:
            return any(list(i.starnormalform() for i in self.list))
        elif self.type == Type.REGEX:
            return self.r.starnormalform()

    def hasEps(self):
        if self.type == Type.K or self.type == Type.Q:
            return True
        elif self.type == Type.C:
            return all(list(i.hasEps() for i in self.list))
        elif self.type == Type.U:
            return any(list(i.hasEps() for i in self.list))
        else:
            return False

    def allHole(self):
        if self.type == Type.K or self.type == Type.Q:
            if self.r.allHole():
                return True
            else:
                return False
        elif self.type == Type.C or self.type == Type.U:
            return all(list(i.allHole() for i in self.list))
        elif self.type == Type.HOLE:
            return True
        else:
            return False

    def redundant_concat1(self):
        if self.type == Type.K or self.type == Type.Q:
            return self.r.redundant_concat1()

        elif self.type == Type.C:
            for index, regex in enumerate(self.list):

                if regex.type == Type.K:
                    # x*x
                    if index+1 < len(self.list) and (regex.r.type == Type.CHAR or regex.r.type == Type.U) and repr(regex.r) == repr(self.list[index+1]):
                        return True
                    elif regex.r.type == Type.C and index+len(regex.r.list) < len(self.list) and not self.list[index+len(regex.r.list)].hasHole():
                        tmp = Concatenate()
                        tmp.list = self.list[index+1:index+len(regex.r.list)+1]
                        if repr(regex.r) == repr(tmp):
                            return True

                    # x*x?
                    elif index+1 < len(self.list) and self.list[index+1].type == Type.Q and repr(regex.r) == repr(self.list[index+1].r):
                        return True

                elif regex.type == Type.Q:
                    # x?x
                    if index + 1 < len(self.list) and (regex.r.type == Type.CHAR or regex.r.type == Type.U) and repr(regex.r) == repr(self.list[index + 1]):
                        return True
                    elif regex.r.type == Type.C and index + len(regex.r.list) < len(self.list) and not self.list[
                        index + len(regex.r.list)].hasHole():
                        tmp = Concatenate()
                        tmp.list = self.list[index + 1:index + len(regex.r.list) + 1]
                        if repr(regex.r) == repr(tmp):
                            return True
                    # x?x*
                    elif index+1 < len(self.list) and self.list[index+1].type == Type.K and repr(regex.r) == repr(self.list[index+1].r):
                        return True

            return any(list(i.redundant_concat1() for i in self.list))

        elif self.type == Type.U:
            return any(list(i.redundant_concat1() for i in self.list))
        elif self.type == Type.REGEX:
            return self.r.redundant_concat1()
        else:
            return False

    def redundant_concat2(self):
        if self.type == Type.K or self.type == Type.Q:
            return self.r.redundant_concat2()

        elif self.type == Type.C:
            for index, regex in enumerate(self.list):

                if regex.type == Type.K:
                    for index2, regex2 in enumerate(self.list):

                        tmp = Concatenate()
                        if index - index2 == 1 or index2 - index  == 1:
                            if regex2.hasEps() and is_inclusive(regex, regex2):
                                return True
                        elif index > index2:
                            tmp.list = self.list[index2:index]
                            if all(list(i.hasEps() for i in tmp.list)) and is_inclusive(regex, tmp):
                                return True
                        elif index < index2:
                            tmp.list = self.list[index + 1:index2 + 1]
                            if all(list(i.hasEps() for i in tmp.list)) and is_inclusive(regex, tmp):
                                return True
                        else:
                            continue

            return any(list(i.redundant_concat2() for i in self.list))

        elif self.type == Type.U:
            return any(list(i.redundant_concat2() for i in self.list))
        elif self.type == Type.REGEX:
            return self.r.redundant_concat2()
        else:
            return False

    def KCK(self):
        if self.type == Type.K:
            if self.r.type == Type.C:

                for index, regex in enumerate(self.r.list):
                    if regex.type == Type.K and not regex.hasHole():
                        left = False
                        right = False
                        if index == 0:
                            left = True
                        elif index == 1:
                            tmp1 = self.r.list[0]
                        else:
                            tmp1 = Concatenate()
                            tmp1.list = self.r.list[0:index]

                        if index == len(self.r.list)-1:
                            right = True
                        elif index == len(self.r.list)-2:
                            tmp2 = self.r.list[len(self.r.list)-1]
                        else:
                            tmp2 = Concatenate()
                            tmp2.list = self.r.list[index+1:len(self.r.list)]

                        if not regex.r.hasEps() and (left or is_inclusive(regex,tmp1)) and (right or is_inclusive(regex,tmp2)):
                            return True

            return self.r.KCK()

        elif self.type == Type.Q:
            return self.r.KCK()

        elif self.type == Type.C or self.type == Type.U:
            return any(list(i.KCK() for i in self.list))
        elif self.type == Type.REGEX:
            return self.r.KCK()
        else:
            return False

    def KCQ(self):
        if self.type == Type.K:
            if self.r.type == Type.C:

                # single symbol
                for index, regex in enumerate(self.r.list):

                    if not regex.hasHole():
                        left = False
                        right = False

                        if index == 0:
                            left = True
                            lefteps = True
                        elif index == 1:
                            tmp1 = self.r.list[0]
                            lefteps = tmp1.hasEps()
                        else:
                            tmp1 = Concatenate()
                            tmp1.list = self.r.list[0:index]
                            lefteps = all(list(i.hasEps() for i in tmp1.list))

                        if index == len(self.r.list) - 1:
                            right = True
                            righteps = True
                        elif index == len(self.r.list) - 2:
                            tmp2 = self.r.list[len(self.r.list) - 1]
                            righteps = tmp2.hasEps()
                        else:
                            tmp2 = Concatenate()
                            tmp2.list = self.r.list[index + 1:len(self.r.list)]
                            righteps = all(list(i.hasEps() for i in tmp2.list))


                        if lefteps and righteps and (left or is_inclusive(KleenStar(regex), tmp1)) and (right or is_inclusive(KleenStar(regex), tmp2)):
                            return True

                # single regex
                for i in range(len(self.r.list)-2):
                    for j in range(i+2, len(self.r.list)):
                        if (i == 0 and j == len(self.r.list)) or j > len(self.r.list):
                            continue
                        regex = Concatenate()
                        regex.list = self.r.list[i:j]


                        if not regex.hasHole():
                            left = False
                            right = False

                            if i == 0:
                                left = True
                                lefteps = True
                            elif i == 1:
                                tmp1 = self.r.list[0]
                                lefteps = tmp1.hasEps()
                            else:
                                tmp1 = Concatenate()
                                tmp1.list = self.r.list[0:i]
                                lefteps = all(list(r.hasEps() for r in tmp1.list))

                            if j == len(self.r.list):
                                right = True
                                righteps = True
                            elif j == len(self.r.list) - 1:
                                tmp2 = self.r.list[len(self.r.list) - 1]
                                righteps = tmp2.hasEps()
                            else:
                                tmp2 = Concatenate()
                                tmp2.list = self.r.list[j + 1:len(self.r.list)]
                                righteps = all(list(i.hasEps() for i in tmp2.list))

                            if lefteps and righteps and (left or is_inclusive(KleenStar(regex), tmp1)) and (
                                    right or is_inclusive(KleenStar(regex), tmp2)):
                                return True

            return self.r.KCQ()

        elif self.type == Type.Q:
            return self.r.KCQ()

        elif self.type == Type.C or self.type == Type.U:
            return any(list(i.KCQ() for i in self.list))
        elif self.type == Type.REGEX:
            return self.r.KCQ()
        else:
            return False

    def QC(self):
        if self.type == Type.K:
            return self.r.QC()

        elif self.type == Type.Q:
            # (xx?)? (xx*)?
            if self.r.type == Type.C and (self.r.list[len(self.r.list)-1].type == Type.K or self.r.list[len(self.r.list)-1].type == Type.Q):
                if len(self.r.list) == 2:
                    tmp = self.r.list[0]
                else:
                    tmp = Concatenate()
                    tmp.list = self.r.list[0:len(self.r.list)-1]
                if repr(tmp) == repr(self.r.list[len(self.r.list)-1].r):
                    return True

            return self.r.QC()

        elif self.type == Type.C or self.type == Type.U:
            return any(list(i.QC() for i in self.list))
        elif self.type == Type.REGEX:
            return self.r.QC()
        else:
            return False

    def OQ(self):
        if self.type == Type.K or self.type == Type.Q:
            return self.r.OQ()
        elif self.type == Type.C:
            return any(list(i.OQ() for i in self.list))
        elif self.type == Type.U:
            for regex in self.list:
                if regex.type == Type.Q:
                    return True
            return any(list(i.OQ() for i in self.list))
        elif self.type == Type.REGEX:
            return self.r.OQ()
        else:
            return False


    def orinclusive(self):
        if self.type == Type.K or self.type == Type.Q:
            return self.r.orinclusive()
        elif self.type == Type.C:
            return any(list(i.orinclusive() for i in self.list))

        elif self.type == Type.U:
            for index, regex in enumerate(self.list):
                for index2, regex2 in enumerate(self.list):
                    if index < index2 and (is_inclusive(regex,regex2) or is_inclusive(regex2,regex)):
                        return True

            for index, regex in enumerate(self.list):
                if regex.orinclusive():
                    return True
            return False

        elif self.type == Type.REGEX:
            return self.r.orinclusive()
        else:
            return False

    def prefix(self):
        if self.type == Type.K or self.type == Type.Q:
            return self.r.prefix()
        elif self.type == Type.C:
            return any(list(i.prefix() for i in self.list))

        elif self.type == Type.U:
            for index1, regex1 in enumerate(self.list):
                if regex1.type == Type.CHAR:
                    for index2, regex2 in enumerate(self.list):
                        if index1 < index2 and regex2.type == Type.CHAR:
                            if repr(regex1) == repr(regex2):
                                return True
                        elif index1 < index2 and regex2.type == Type.C:
                            if repr(regex1) == repr(regex2.list[0]):
                                return True
                            if repr(regex1) == repr(regex2.list[len(regex2.list) - 1]):
                                return True

                if regex1.type == Type.C:
                    for index2, regex2 in enumerate(self.list):
                        if index1 < index2 and regex2.type == Type.C:
                            if repr(regex1.list[0]) == repr(regex2.list[0]):
                                return True
                            if repr(regex1.list[len(regex1.list) - 1]) == repr(regex2.list[len(regex2.list) - 1]):
                                return True

            return any(list(i.prefix() for i in self.list))
        elif self.type == Type.REGEX:
            return self.r.prefix()
        else:
            return False

    def sigmastar(self):
        if self.type == Type.K:
            if repr(self.r) != '0|1':
                return bool(re.fullmatch(repr(self.r), '0')) and bool(re.fullmatch(repr(self.r), '1'))

            return self.r.sigmastar()
        elif self.type == Type.Q:
            return self.r.sigmastar()
        elif self.type == Type.C or self.type == Type.U:
            return any(list(i.sigmastar() for i in self.list))
        elif self.type == Type.REGEX:
            return self.r.sigmastar()
        else:
            return False

    def alpha(self):
        if self.type == Type.K:
            if self.r.type == Type.C and len(self.r.list) == 2:
                if self.r.list[1].type == Type.K and self.r.list[0] == self.r.list[1].r:
                    return True
                if self.r.list[0].type == Type.K and self.r.list[0].r == self.r.list[1]:
                    return True
                if self.r.list[1].type == Type.Q and self.r.list[0] == self.r.list[1].r:
                    return True
                if self.r.list[0].type == Type.Q and self.r.list[0].r == self.r.list[1]:
                    return True

            return self.r.alpha()

        if self.type == Type.Q:
            if self.r.type == Type.C and len(self.r.list) == 2:
                if self.r.list[1].type == Type.K and self.r.list[0] == self.r.list[1].r:
                    return True
                if self.r.list[0].type == Type.K and self.r.list[0].r == self.r.list[1]:
                    return True


            return self.r.alpha()


        elif self.type == Type.C:
            for index, regex in enumerate(self.list):

                if regex.type == Type.K:
                    #x*x?
                    if index+1 < len(self.list) and self.list[index+1].type == Type.Q and repr(regex.r) == repr(self.list[index+1].r):
                        return True
                    #x*x*
                    if index+1 < len(self.list) and self.list[index+1].type == Type.K and repr(regex.r) == repr(self.list[index+1].r):
                        return True
                elif regex.type == Type.Q:
                    #x?x*
                    if index+1 < len(self.list) and self.list[index+1].type == Type.K and repr(regex.r) == repr(self.list[index+1].r):
                        return True

            return any(list(i.alpha() for i in self.list))

        elif self.type == Type.U:

            for index, regex in enumerate(self.list):
                for index2, regex2 in enumerate(self.list):
                    if index < index2 and (is_inclusive(regex, regex2) or is_inclusive(regex2, regex)):
                        return True

            for index, regex in enumerate(self.list):

                if regex.alpha():
                    return True

            return False
        elif self.type == Type.REGEX:
            return self.r.alpha()
        else:
            return False



class Hole(RE):
    def __init__(self):
        self.level = 0
        self.type = Type.HOLE
    def __repr__(self):
        return '#'
    def repr4(self):
        return [[self.level, '#']]
    def repr_unsp(self):
        return [[self.level, '#']]
    def reprunroll(self):
        return [[self.level, '#']]
    def reprsplit(self):
        return [[self.level, '#']]
    def reprAlpha(self):
        return [[self.level, '#']]
    def reprAlpha2(self):
        return [[self.level, '#']]
    def reprNew(self):
        return [[self.level, '#']]

    def hasHole(self):
        return True
    def unrolled(self):
        return False
    def getCost(self):
        return HOLE_COST

class REGEX(RE):
    def __init__(self, r = Hole()):
        self.r = r
        self.type = Type.REGEX
        self.lastRE = Type.REGEX
        self.unrolled2 = False
    def __repr__(self):
        return repr(self.r)
    def spreadAll(self):
        return self.r.spreadAll()
    def spreadNP(self):
        return self.r.spreadNP()
    def repr4(self):
        return self.r.repr4()
    def repr_unsp(self):
        return self.r.repr_unsp()
    def reprAlpha(self):
        return self.r.reprAlpha()

    def reprAlpha2(self):
        return self.r.reprAlpha2()

    def reprNew(self):
        return self.r.reprNew()

    def hasHole(self):
        return self.r.hasHole()
    def unrolled(self):
        return self.r.unrolled()
    def getCost(self):
        return self.r.getCost()

class Epsilon(RE):
    def __init__(self):
        self.level = 0
        self.type = Type.EPS
    def __repr__(self):
        return '@epsilon'
    def hasHole(self):
        return False
    def unrolled(self):
        return False

class Character(RE):
    def __init__(self, c):
        self.c = c
        self.level = 0
        self.type = Type.CHAR
    def __repr__(self):
        return self.c
    def spreadAll(self):
        return self.c
    def spreadNP(self):
        return self.c
    def repr4(self):
        return [[self.level, repr(self)]]
    def repr_unsp(self):
        return [[self.level, repr(self)]]
    def reprunroll(self):
        return [[self.level, repr(self)]]
    def reprsplit(self):
        return [[self.level, repr(self)]]
    def reprAlpha(self):
        return [[self.level, repr(self)]]
    def reprAlpha2(self):
        return [[self.level, repr(self)]]
    def reprNew(self):
        return [[self.level, repr(self)]]
    def hasHole(self):
        return False
    def unrolled(self):
        return False
    def getCost(self):
        return SYMBOL_COST

class KleenStar(RE):
    def __init__(self, r=Hole()):
        self.r = r
        self.level = 1
        self.string = None
        self.hasHole2 = True
        self.type = Type.K
        self.unrolled2 = False

    def __repr__(self):
        if self.string:
            return self.string

        if '{}'.format(self.r) == '@emptyset':
            self.string = '@epsilon'
            return self.string

        if '{}'.format(self.r) == '@epsilon':
            self.string = '@epsilon'
            return self.string


        if self.r.level > self.level:
            self.string = '({})*'.format(self.r)
            return self.string
        else:
            self.string = '{}*'.format(self.r)
            return self.string

    def spreadAll(self):
        if self.r.type == Type.HOLE:
            return '({})*'.format(KleenStar(Or(Character('0'), Character('1'))))
        if self.r.level > self.level:
                return '({})*'.format(self.r.spreadAll())
        else:
                return '{}*'.format(self.r.spreadAll())

    def spreadNP(self):
        if self.r.type == Type.HOLE:
            return '@epsilon'

        if '{}'.format(self.r.spreadNP()) == '@emptyset':
            return '@epsilon'

        if '{}'.format(self.r.spreadNP()) == '@epsilon':
            return '@epsilon'

        if self.r.level > self.level:
            return '({})*'.format(self.r.spreadNP())
        else:
            return '{}*'.format(self.r.spreadNP())


    def reprAlpha2(self):
        return [[1, repr(self)]]


    def hasHole(self):
        if not self.hasHole2:
            return False

        if not self.r.hasHole():
            self.hasHole2 = False
        return self.hasHole2

    def unrolled(self):
        if self.unrolled2 or self.r.unrolled():
            return True
        else:
            return False

    def getCost(self):
        return CLOSURE_COST + self.r.getCost()


class Question(RE):
    def __init__(self, r=Hole()):
        self.r = r
        self.level = 1
        self.string = None
        self.hasHole2 = True
        self.type = Type.Q
        self.unrolled2 = False

    def __repr__(self):
        if self.string:
            return self.string

        if '{}'.format(self.r) == '@emptyset':
            self.string = '@epsilon'
            return self.string

        if '{}'.format(self.r) == '@epsilon':
            self.string = '@epsilon'
            return self.string

        if self.r.level > self.level:
            self.string = '({})?'.format(self.r)
            return self.string
        else:
            self.string = '{}?'.format(self.r)
            return self.string

    def spreadAll(self):

        if self.r.type == Type.HOLE:
            return '({})?'.format(KleenStar(Or(Character('0'), Character('1'))))
        elif self.r.level > self.level:
            return '({})?'.format(self.r.spreadAll())
        else:
            return '{}?'.format(self.r.spreadAll())

    def spreadNP(self):
        if self.r.type == Type.HOLE:
            return '@epsilon'

        if '{}'.format(self.r.spreadNP()) == '@emptyset':
            return '@epsilon'

        if '{}'.format(self.r.spreadNP()) == '@epsilon':
            return '@epsilon'


        if self.r.level > self.level:
            return '({})?'.format(self.r.spreadNP())
        else:
            return '{}?'.format(self.r.spreadNP())

    def reprAlpha2(self):
        return [[1, repr(self)]]


    def hasHole(self):
        if not self.hasHole2:
            return False

        if not self.r.hasHole():
            self.hasHole2 = False
        return self.hasHole2

    def unrolled(self):
        if self.unrolled2 or self.r.unrolled():
            return True
        else:
            return False

    def getCost(self):
        return  CLOSURE_COST + self.r.getCost()

class Concatenate(RE):
    def __init__(self, *regexs):
        self.list = list()
        for regex in regexs:
            self.list.append(regex)
        self.level = 2
        self.string = None
        self.hasHole2 = True
        self.type = Type.C
        self.unrolled2 = False

    def __repr__(self):
        if self.string:
            return self.string

        def formatSide(side):
            if side.level > self.level:
                return '({})'.format(side)
            else:
                return '{}'.format(side)
        for regex in self.list:
            if '@emptyset' in repr(regex):
                self.string = '@emptyset'
                return self.string

        str_list = []
        for regex in self.list:
            if '@epsilon' != repr(regex):
                str_list.append(formatSide(regex))
        return ''.join(str_list)

    def spreadAll(self):

        def formatSide(side):
            if side.level > self.level:
                return '({})'.format(side.spreadAll())
            else:
                return '{}'.format(side.spreadAll())

        str_list = []
        for regex in self.list:
            if regex.type == Type.HOLE:
                str_list.append(formatSide(KleenStar(Or(Character('0'), Character('1')))))
            else:
                str_list.append(formatSide(regex))
        return ''.join(str_list)

    def spreadNP(self):

        def formatSide(side):
            if side.level > self.level:
                return '({})'.format(side.spreadNP())
            else:
                return '{}'.format(side.spreadNP())

        for regex in self.list:
            if regex.type == Type.HOLE or '@emptyset' in regex.spreadNP():
                return '@emptyset'

        str_list = []
        for regex in self.list:
            if '@epsilon' != regex.spreadNP():
                if regex.type == Type.HOLE:
                    str_list.append(formatSide(Character('@emptyset')))
                else:
                    str_list.append(formatSide(regex))
        return ''.join(str_list)

    def reprAlpha2(self):
            result = []

            for index1, regex in enumerate(self.list):
                sp = regex.reprAlpha2()
                if len(sp) != 1:
                    for level_str in sp:
                        str_list = []
                        for index2, regex2 in enumerate(self.list):
                            if index1 == index2:
                                if level_str[0] > self.level:
                                    str_list.append('({})'.format(level_str[1]))
                                else:
                                    str_list.append('{}'.format(level_str[1]))
                            else:
                                if regex2.type == Type.U:
                                    str_list.append('({})'.format(repr(regex2)))
                                else:
                                    str_list.append(repr(regex2))
                        result.append([self.level, ''.join(str_list)])


            if not result:
                return [[self.level, repr(self)]]

            return result



    def hasHole(self):
        if not self.hasHole2:
            return False

        self.hasHole2 = any(list(i.hasHole() for i in self.list))
        return self.hasHole2
    def unrolled(self):
        if self.unrolled2:
            return True

        self.unrolled2 = any(list(i.unrolled() for i in self.list))
        return self.unrolled2

    def getCost(self):
        return CONCAT_COST + sum(list(i.getCost() for i in self.list))

class Or(RE):
    def __init__(self, a=Hole(), b=Hole()):
        self.list = list()
        self.list.append(a)
        self.list.append(b)
        self.level = 3
        self.string = None
        self.hasHole2 = True
        self.type = Type.U
        self.unrolled2 = False

    def __repr__(self):
        if self.string:
            return self.string

        def formatSide(side):
            if side.level > self.level:
                return '({})'.format(side)
            else:
                return '{}'.format(side)

        str_list = []
        for regex in self.list:
            if repr(regex) != '@emptyset':
                if str_list:
                    str_list.append("|")
                str_list.append(formatSide(regex))
        if not str_list:
            return '@emptyset'
        else:
            return ''.join(str_list)

    def spreadAll(self):

        def formatSide(side):
            if side.level > self.level:
                return '({})'.format(side.spreadAll())
            else:
                return '{}'.format(side.spreadAll())

        str_list = []
        for regex in self.list:
            if str_list:
                str_list.append("|")
            if regex.type == Type.HOLE:
                str_list.append(formatSide(KleenStar(Or(Character('0'), Character('1')))))
            else:
                str_list.append(formatSide(regex))

        return ''.join(str_list)

    def spreadNP(self):

        def formatSide(side):
            if side.level > self.level:
                return '({})'.format(side.spreadNP())
            else:
                return '{}'.format(side.spreadNP())

        str_list = []
        for regex in self.list:
            if regex.type != Type.HOLE and regex.spreadNP() != '@emptyset':
                if str_list:
                    str_list.append("|")
                if regex.type == Type.HOLE:
                    str_list.append(formatSide(Character('@emptyset')))
                else:
                    str_list.append(formatSide(regex))
        if not str_list:
            return '@emptyset'
        else:
           return ''.join(str_list)


    def reprAlpha2(self):
        result = []

        for regex in self.list:
            for level_str in regex.reprAlpha2():
                if level_str[1] == '(0|1)*':
                    continue
                elif level_str[0] > self.level:
                    result.append([level_str[0], '({})'.format(level_str[1])])
                else:
                    result.append([level_str[0], '{}'.format(level_str[1])])

        if not result:
            return [[1, '(0+1)*']]
        return result

    def hasHole(self):
        if not self.hasHole2:
            return False

        self.hasHole2 = any(list(i.hasHole() for i in self.list))
        return self.hasHole2

    def unrolled(self):
        if self.unrolled2:
            return True

        self.unrolled2 = any(list(i.unrolled() for i in self.list))
        return self.unrolled2

    def getCost(self):
        return UNION_COST + sum(list(i.getCost() for i in self.list))