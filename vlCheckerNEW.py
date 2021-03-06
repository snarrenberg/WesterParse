# -----------------------------------------------------------------------------
# Name:         vlChecker.py
# Purpose:      Framework for analyzing voice leading in species counterpoint
#
# Author:       Robert Snarrenberg
# Copyright:    (c) 2021 by Robert Snarrenberg
# License:      BSD, see license.txt
# -----------------------------------------------------------------------------
"""Take a score (source) with two or more parts (lines)
and examine the local counterpoint 
for conformity with Westergaard's rules of species counterpoint.
"""

# NB: vlq parts and score Parts are numbered top to bottom
# NB: vPair parts are numbered bottom to top

import itertools
import unittest
import logging

from music21 import *

# from westerparse import csd
from westerparse import context
from westerparse import theoryAnalyzerWP
# from westerparse import theoryResultWP

# -----------------------------------------------------------------------------
# LOGGER
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# logging handlers
f_handler = logging.FileHandler('vl.txt', mode='w')
f_handler.setLevel(logging.DEBUG)
# logging formatters
f_formatter = logging.Formatter('%(message)s')
f_handler.setFormatter(f_formatter)
# add handlers to logger
logger.addHandler(f_handler)

# -----------------------------------------------------------------------------
# MODULE VARIABLES
# -----------------------------------------------------------------------------

# variables set by instructor
allowSecondSpeciesBreak = True
checkSonorities = False

vlErrors = []

# settings for testing
# paceUnit = 4.0 # pace unit for first-species notes, in quarter-note lengths
# TODO infer pace unit from meter for species counterpoint
#   paceUnit = xxxxx.getContextByClass('Measure').barDuration.quarterLength
#   find the slowest moving line and take it as the Cf?

# -----------------------------------------------------------------------------
# MAIN FUNCTIONS
# -----------------------------------------------------------------------------


def voiceLeadingAnalyzer(context):
    """A function for processing and reporting on voice leading 
    in species counterpoint, in both simple and mixed species 
    in two to four parts."""

    # list of errors for reporting
    sonorityErrors = []
    
    if len(context.parts) == 1:
        print('The composition is only a single line. '
              'There is no voice-leading to check.')

    # extract relevant information from the score, if contrapuntal
    # using revised versions of music21 theory modules
    analytics = theoryAnalyzerWP.Analyzer()
    analytics.addAnalysisData(context.score)

    paceUnit = context.score.getContextByClass('Measure').barDuration.quarterLength

    voiceLeadingErrors = checkVoiceLeading(context.score, analytics)
    checkFourthLeapsInBass(context.score, analytics)

#    checkFinalStep(context.score, analytics)
    checkControlOfDissonance(context.score, analytics)

    if checkSonorities:
        getAllSonorities(context, analytics)
        pass

    report = True
    # report voice-leading errors, if asked
    if report == True:
        if voiceLeadingErrors == []:
            print('No voice-leading errors found.\n')
        else:
            print('Voice Leading Report \n\n\tThe following '
                  'voice-leading errors were found:')
            for error in voiceLeadingErrors: print('\t\t' + error)
            print('\n\n')

    # report sonority errors, if asked
    if checkSonorities:
        if sonorityErrors == []:
            print('No sonority errors found.\n')
        else:
            print('Sonority Report \n\n\tThe following '
                  'sonority errors were found:')
            for error in sonorityErrors: print('\t\t' + error)
            print('\n\n')

    else: pass

# utility function for finding pairs of parts    
def getAllPartNumPairs(score):
    """from theory analyzer"""
    partNumPairs = []
    numParts = len(score.parts)
    for partNum1 in range(numParts - 1):
        for partNum2 in range(partNum1 + 1, numParts):
            partNumPairs.append((partNum1, partNum2))
    return partNumPairs    
    

# -----------------------------------------------------------------------------
# METHODS FOR EVALUATING VOICE LEADING, BY SPECIES
# -----------------------------------------------------------------------------

def species(note):
    if note.quarterLength == paceUnit:
        return 'first'
    # consider adding criteria for second and fourth species in
    # triple meter: 2*(paceUnit/3)
    if note.quarterLength == paceUnit/2 and note.isNote and not note.tie:
        return 'second'
    if note.quarterLength == paceUnit/2 and note.isNote and note.tie:
        return 'fourth'
    if note.quarterLength >= paceUnit/3 and note.isNote:
        return 'third'                    
    if note.quarterLength >= paceUnit/4 and note.isNote:
        return 'third'
    if note.quarterLength == paceUnit/2 and note.isNote and note.tie:
        return 'fourth'


def checkConsecutions(score):
    for part in score.parts:
        if part.species in ['second', 'third']:
            for n in part.recurse().notes:
                if n.consecutions.leftType == 'same':
                    error = 'Direct repetition in bar ' + str(n.measureNumber)
                    vlErrors.append(error)
        if part.species == 'fourth':
            for n in part.recurse().notes:
                if n.tie:
                    if n.tie.type == 'start' and n.consecutions.rightType != 'same':
                        error = 'Pitch not tied across the barline into bar ' + str(n.measureNumber+1)
                        vlErrors.append(error)
                    elif n.tie.type == 'stop' and n.consecutions.leftType != 'same':
                        error = 'Pitch not tied across the barline into bar ' + str(n.measureNumber)
                        vlErrors.append(error)
                # TODO allow breaking into second species
                elif not n.tie:
                    if n.consecutions.rightType == 'same':
                        error = 'Direct repetition around bar ' + str(n.measureNumber)
                        vlErrors.append(error)


def checkFinalStep(score, analyzer, partNum1=0, partNum2=None):
    # TODO rewrite based on parser's lineType value
    # determine whether the the upper part is a primary upper line
    # if score.parts[partNum1].isPrimary == True:
    if score.parts[partNum1].id == 'Primary Upper Line':
        # assume there is no acceptable final step connection until proven true
        finalStepConnection = False
        # get the last note of the primary upper line
        ultimaNote = score.parts[partNum1].recurse().notes[-1]
        # get the penultimate note of the bass 
        penultBass = score.parts[partNum2].recurse().notes[-2]
        # collect the notes in the penultimate bar of the upper line
        penultBar = score.parts[partNum1].getElementsByClass(stream.Measure)[-2].notes
        buffer = []
        stack = []
        def shiftBuffer(stack, buffer):
            nextnote = buffer[0]
            buffer.pop(0)
            stack.append(nextnote)            
        # fill buffer with notes of penultimate bar in reverse
        for n in reversed(penultBar): 
            buffer.append(n)
        blen = len(buffer)
        # start looking for a viable step connection
        while blen > 0:
            if isDiatonicStep(ultimaNote, buffer[0]) and isConsonanceAboveBass(penultBass, buffer[0]):
                # check penultimate note
                if len(stack) == 0:
                    finalStepConnection = True
                    break
                # check other notes, if needed
                elif len(stack) > 0:
                    for s in stack:
                        if isDiatonicStep(s, buffer[0]):
                            finalStepConnection = False
                            break
                        else:
                            finalStepConnection = True
            shiftBuffer(stack, buffer)
            blen = len(buffer)
        if finalStepConnection == False:
            error = 'No final step connection in the primary upper line'
            vlErrors.append(error)
    else:
        pass


def checkVoiceLeading(score, analyzer):
    # assume that parts are properly sorted high to low
    # verticality objects are numbered high to low
    # check voice leading by rhythmic situation
    partNumPairs = getAllPartNumPairs(score)
    vertList = analyzer.getVerticalities(score, classFilterList=('Note',
                                                                 'Rest'))
    # collect the relevant nonconsecutive verticalities
    # determine the species of a part at each downbeat, to eventually
    # allow for lines in fifth species

    # voiceleading.Verticality.contentDict consists of partNums as keys and
    # lists of m21Objects as values
    # e.g., voiceLeading.Verticality({0:[note.Note('A4')], 1: [note.Note('F2')]})
    # in species counterpoint, the lists are always just single notes,
    # so list[0] suffices as reference

    for vert in vertList[0:3]:
        firstSpeciesParts = []
        secondSpeciesParts = []
        thirdSpeciesParts = []
        fourthSpeciesParts = []
        # k = partNum, v = noteList
        for k,v in vert.contentDict.items():
            if species(v[0]) == 'first':
                firstSpeciesParts.append(k)
            if species(v[0]) == 'second':
                secondSpeciesParts.append(k)
            if species(v[0]) == 'third':
                thirdSpeciesParts.append(k)
            if species(v[0]) == 'fourth':
                fourthSpeciesParts.append(k)

        vlPairs = pairwiseFromList(firstSpeciesParts)
        if vlPairs: print('vl pairs, first-first', vlPairs)
        vlPairs = pairwiseFromLists(firstSpeciesParts, secondSpeciesParts)
        if vlPairs: print('vl pairs, first-second', vlPairs)
        vlPairs = pairwiseFromLists(firstSpeciesParts, thirdSpeciesParts)
        if vlPairs: print('vl pairs, first-third', vlPairs)
        vlPairs = pairwiseFromLists(firstSpeciesParts, fourthSpeciesParts)
        if vlPairs: print('vl pairs, first-fourth', vlPairs)

    for vert in vertList:

        # SET A: second and fourth species nonconsecutives: off to off
        # first-second: off the beat to off the beat
        # first-fourth: off the beat to off the beat
        rules = [vert.offset(leftAlign=False) % paceUnit == paceUnit/2]
        if all(rules):
            vertOffset = vert.offset(leftAlign=False)
            # find the parts based on duration of notes relative to the prevailing meter
            firstSpeciesParts = []
            secondSpeciesParts = []
            fourthSpeciesParts = []
            for k,v in vert.contentDict.items():
                if species(v[0]) == 'first':
                    firstSpeciesParts.append(k)
                if species(v[0]) == 'second':
                    secondSpeciesParts.append(k)
                if species(v[0]) == 'fourth':
                    fourthSpeciesParts.append(k)
            # use pairs extracted from firstSpeciesParts, secondSpeciesParts, always ordered lower,higher
            
            # first-second
            vlPairs = pairwiseFromLists(firstSpeciesParts, secondSpeciesParts)
            for vlp in vlPairs:
                # find the next offbeat vert and make a vlq
                nextOffbeatVert = [v for v in vertList if v.offset(leftAlign=False) == (vertOffset+paceUnit)]
                if nextOffbeatVert == []:
                    break
                v1partNum = vlp[0]
                v2partNum = vlp[1]
                v1n1 = vert.getObjectsByPart(vlp[0])
                v1n2 = nextOffbeatVert[0].getObjectsByPart(vlp[0])
                v2n1 = vert.getObjectsByPart(vlp[1])
                v2n2 = nextOffbeatVert[0].getObjectsByPart(vlp[1])
                vlq = voiceLeading.VoiceLeadingQuartet(v1n1, v1n2, v2n1, v2n2)
                # rules from Westergaard p. 116
                #     no parallel unisons
                rules0 = [isParallelUnison(vlq)]
                if all(rules0):
                    error = 'Forbidden parallel unisons off the beats in bars ' \
                            + str(vlq.v1n1.measureNumber) + '-' + str(vlq.v1n2.measureNumber)
                    vlErrors.append(error)
                #    no parallel octaves unless conditions are met
                rules1 = [isParallelOctave(vlq)]
                rules2 = [isDiatonicStep(v1n1,v1n2)]
                rules3a = [v1partNum in secondSpeciesParts,
                    v1n1.consecutions.leftDirection != v1n2.consecutions.leftDirection]
                rules3b = [v2partNum in secondSpeciesParts,
                    v2n1.consecutions.leftDirection != v2n2.consecutions.leftDirection]
                rules4a = [v1partNum in secondSpeciesParts,
                    v1n1.consecutions.rightType == 'step']
                rules4b = [v2partNum in secondSpeciesParts,
                    v2n1.consecutions.rightType == 'step']
                if all(rules1) and all(rules2) and not (all(rules3a) or all(rules3b)):
                    error = 'Forbidden parallel octaves off the beats in bars ' \
                        + str(vlq.v1n1.measureNumber) + '-' + str(vlq.v1n2.measureNumber)
                    vlErrors.append(error)
                if all(rules1) and not all(rules2):
                    if not ((all(rules3a) or all(rules3b)) or (all(rules4a) or all(rules4b))):
                        error = 'Forbidden parallel octaves off the beats in bars ' \
                            + str(vlq.v1n1.measureNumber) + '-' + str(vlq.v1n2.measureNumber)
                        vlErrors.append(error)

            # first-fourth
            vlPairs = pairwiseFromLists(firstSpeciesParts,fourthSpeciesParts)
            for vlp in vlPairs:
                # TODO find a better way to get the intervening onbeat verticality
                nextOnbeatVert = [v for v in vertList if v.offset(leftAlign=False) == (vertOffset+(paceUnit/2))]
                nextOffbeatVert = [v for v in vertList if v.offset(leftAlign=False) == (vertOffset+paceUnit)]
                v1partNum = vlp[0]
                v2partNum = vlp[1]
                v1n1 = vert.getObjectsByPart(vlp[0])
                v1n2 = nextOffbeatVert[0].getObjectsByPart(vlp[0])
                v2n1 = vert.getObjectsByPart(vlp[1])
                v2n2 = nextOffbeatVert[0].getObjectsByPart(vlp[1])
                vlq = voiceLeading.VoiceLeadingQuartet(v1n1, v1n2, v2n1, v2n2)
                # rules from Westergaard p. 150
                #     no parallel unisons
                rules0 = [isParallelUnison(vlq)]
                if all(rules0):
                    error = 'Forbidden parallel unisons off the beats in bars ' \
                            + str(vlq.v1n1.measureNumber) + '-' + str(vlq.v1n2.measureNumber)
                    vlErrors.append(error)
                #    no parallel octaves unless conditions are met
                rules1 = [isParallelOctave(vlq)]
                rules2 = [v1partNum == len(score.parts)-1,
                        v1partNum == len(score.parts)-1]
                interveningComponents = [nextOnbeatVert[0].getObjectsByPart(v1partNum),nextOnbeatVert[0].getObjectsByPart(v2partNum)]
                rules3a = [isConsonanceAboveBass(interveningComponents[1], interveningComponents[0])]
                rules3b = [isConsonanceBetweenUpper(interveningComponents[1], interveningComponents[0])]
                if all(rules1) and (any(rules2) and not all(rules3a)) or (not any(rules2) and not all(rules3b)):
                    error = 'Forbidden parallel octaves off the beats in bars ' \
                            + str(vlq.v1n1.measureNumber) + '-' + str(vlq.v1n2.measureNumber)
                    vlErrors.append(error)
                    
        # SET B: third species nonconsecutives, off to next on
        # first-third: off to next (but not immediately following) on the beat

        # find a way to filter out all verts that are on or just before a beat



    lenvl = len(vertList)
    offbeatVerts = []
    for i, elem in enumerate(vertList):
        thiselem = elem
        nextelem = vertList[(i+1) % lenvl]#
        if nextelem.offset(leftAlign=False) % paceUnit == 0: 
            pass
        elif thiselem.offset(leftAlign=False) % paceUnit == 0:
            pass
        else:
            offbeatVerts.append(thiselem)
    for vert in offbeatVerts:
        vertOffset = vert.offset(leftAlign=False)
        # find the parts based on duration of notes relative to the prevailing meter
        firstSpeciesParts = []
        thirdSpeciesParts = []
        for k,v in vert.contentDict.items():
            if species(v[0]) == 'first':
                firstSpeciesParts.append(k)
            if species(v[0]) == 'third':
                thirdSpeciesParts.append(k)
            
        # use pairs extracted from firstSpeciesParts, secondSpeciesParts, always ordered lower,higher
        vlPairs = pairwiseFromLists(firstSpeciesParts,thirdSpeciesParts)
        for vlp in vlPairs:
            # get the next onbeat verticality
            nextOnbeat = vert.offset(leftAlign=True) + paceUnit
            nextOnbeatVert = [v for v in vertList if v.offset(leftAlign=True) == nextOnbeat]
            # don't continue if ...
            if not nextOnbeatVert: break
            v1partNum = vlp[0]
            v2partNum = vlp[1]
            v1n1 = vert.getObjectsByPart(vlp[0])
            v1n2 = nextOnbeatVert[0].getObjectsByPart(vlp[0])
            v2n1 = vert.getObjectsByPart(vlp[1])
            v2n2 = nextOnbeatVert[0].getObjectsByPart(vlp[1])
            vlq = voiceLeading.VoiceLeadingQuartet(v1n1, v1n2, v2n1, v2n2)
            # rules from Westergaard p. 132
            #     no parallel unisons
            rules0 = [isParallelUnison(vlq)]
            if all(rules0):
                error = 'Forbidden parallel unisons from off the beat to next \
                        (but not immediately following) on the beat in bars ' \
                        + str(vlq.v1n1.measureNumber) + '-' + str(vlq.v1n2.measureNumber)
                vlErrors.append(error)
            #     no parallel octaves unless conditions are met
            parDirection = interval.Interval(vlq.v1n1, vlq.v1n2).direction
            rules1 = [isParallelOctave(vlq)]
            if all(rules1):
                # get all the notes in the first bar of the third species part
                if v1partNum in thirdSpeciesParts: 
                    speciesPartNum = v1partNum
                else: 
                    speciesPartNum = v2partNum
                firstMeasureNotes = [n for n in score.parts[speciesPartNum].flat.notes if n.measureNumber == v1n1.measureNumber]
                # get the onbeat note in the third species part
                if v1partNum == speciesPartNum:
                    secondMeasureNote = v1n2
                else:
                    secondMeasureNote = v2n2
                rules2a = [v1partNum in thirdSpeciesParts,
                    v1n2.consecutions.leftType == 'step',
                    v1n2.consecutions.rightType == 'step',
                    v1n2.consecutions.leftDirection != parDirection,
                    v1n2.consecutions.rightDirection != parDirection]
                rules2b = [v2partNum in thirdSpeciesParts,
                    v2n2.consecutions.leftType == 'step',
                    v2n2.consecutions.rightType == 'step',
                    v2n2.consecutions.leftDirection != parDirection,
                    v2n2.consecutions.rightDirection != parDirection]
                rules3 = [secondMeasureNote in firstMeasureNotes]
                # TODO verify that the rules work by testing with faulty examples
                if not ((all(rules2a) or all(rules2b)) or all(rules3)):
                    error = 'Forbidden parallel octaves from off the beat to next ' + \
                            '(but not immediately following) on the beat in bars ' \
                            + str(vlq.v1n1.measureNumber) + '-' + str(vlq.v1n2.measureNumber)
                    vlErrors.append(error)
        

    for vert in vertList:                       
        # first-second: on the beat to on the beat
        # first-fourth: on the beat to on the beat (p. 150)    
        if vert.offset(leftAlign=False) % paceUnit == 0.0:
            vertOffset = vert.offset(leftAlign=False)
            # find the parts based on duration of notes relative to the prevailing meter
            firstSpeciesParts = []
            secondSpeciesParts = []
            fourthSpeciesParts = []
            for k,v in vert.contentDict.items():
                if species(v[0]) == 'first':
                    firstSpeciesParts.append(k)
                if species(v[0]) == 'second':
                    secondSpeciesParts.append(k)
                if species(v[0]) == 'fourth':
                    fourthSpeciesParts.append(k)
            
            # first-second
            vlPairs = pairwiseFromLists(firstSpeciesParts,secondSpeciesParts)
            for vlp in vlPairs:
                nextOnbeatVert = [v for v in vertList if v.offset(leftAlign=False) == (vertOffset+paceUnit)]
                if nextOnbeatVert == []:
                    break
                v1partNum = vlp[0]
                v2partNum = vlp[1]
                v1n1 = vert.getObjectsByPart(vlp[0])
                v1n2 = nextOnbeatVert[0].getObjectsByPart(vlp[0])
                v2n1 = vert.getObjectsByPart(vlp[1])
                v2n2 = nextOnbeatVert[0].getObjectsByPart(vlp[1])
                vlq = voiceLeading.VoiceLeadingQuartet(v1n1, v1n2, v2n1, v2n2)
                # rules from Westergaard p. 115
                #     no parallel unisons
                rules0 = [isParallelUnison(vlq)]
                if all(rules0):
                    error = 'Forbidden parallel unisons on the beats in bars ' \
                            + str(vlq.v1n1.measureNumber) + '-' + str(vlq.v1n2.measureNumber)
                    vlErrors.append(error)
                #     no parallel octaves 
                rules1 = [isParallelOctave(vlq)]
                if all(rules1):
                    error = 'Forbidden parallel octaves on the beats in bars ' \
                            + str(vlq.v1n1.measureNumber) + '-' + str(vlq.v1n2.measureNumber)
                    vlErrors.append(error)
                #     no parallel fifths unless conditions are met
                rules2 = [isParallelFifth(vlq)]
                parDirection = interval.Interval(vlq.v1n1, vlq.v1n2).direction
                if all(rules2):
                    if v1partNum in secondSpeciesParts: 
                        speciesPartNum = v1partNum
                    else: 
                        speciesPartNum = v2partNum
                    rules3a = [v1partNum in secondSpeciesParts,
                        v1n2.consecutions.leftType == 'step',
                        v1n2.consecutions.rightType == 'step',
                        v1n2.consecutions.leftDirection != parDirection,
                        v1n2.consecutions.rightDirection != parDirection]
                    rules3b = [v2partNum in secondSpeciesParts,
                        v2n2.consecutions.leftType == 'step',
                        v2n2.consecutions.rightType == 'step',
                        v2n2.consecutions.leftDirection != parDirection,
                        v2n2.consecutions.rightDirection != parDirection]
                    rules3 = [secondMeasureNote in firstMeasureNotes]
                    # TODO verify that the rules work by testing with faulty examples
                    if not (all(rules3a) or all(rules3b)):
                        error = 'Forbidden parallel fifths on the beats in bars ' \
                                + str(vlq.v1n1.measureNumber) + '-' + str(vlq.v1n2.measureNumber)
                        vlErrors.append(error)
                #     no cross relations unless conditions are met
                


    onbeatVerts = []# [v for v in vertList if v.beatStrength == 1.0]
    offbeatVerts = []
    
    vertPairsConsecutive = pairwise(vertList)
    vertPairsOnbeat = pairwise(onbeatVerts)
    
    # get all the pairs of consecutive verticalities
    for vertPair in vertPairsConsecutive:
        # get all the VLQs in these pairs, keyed by partNumPairs
        vlqList = makeVLQsFromVertPair(vertPair, partNumPairs)
        for vlqInstance in vlqList:
            partNumPair = vlqInstance[0]
            vlq = vlqInstance[1]
            otherParts = [p for p in range(0, len(score.parts)) if p not in partNumPair]

            # check motion to new simultaneity
            rules1 = [vlq.v1n2.offset == vlq.v2n2.offset]
            if all(rules1):
                if isSimilarUnison(vlq):
                    error = 'XXX Forbidden similar motion to unison going INTO bar ' + str(vlq.v2n2.measureNumber)
                    vlErrors.append(error)
                if isSimilarFromUnison(vlq):
                    error = 'XXX Forbidden similar motion from unison IN bar ' + str(vlq.v2n1.measureNumber)
                    vlErrors.append(error)
                if isSimilarOctave(vlq):
                    rules = [vlq.hIntervals[0].name in ['m2', 'M2'],
                            vlq.v1n2.csd.value % 7 == 0,
                            vlq.v1n2.measureNumber == score.measures,
                            vlq.v2n2.measureNumber == score.measures]
                    if not all(rules):
                        error = 'XXX Forbidden similar motion to octave going INTO bar ' + str(vlq.v2n2.measureNumber)
                        vlErrors.append(error)
                if isSimilarFifth(vlq) and vlq.v1n2.beat == 1:
                    # TODO rule is restricted to onbeat fifths, Westergaard p. 161
                    rules1 = [vlq.hIntervals[0].name in ['m2', 'M2']]
                    rules2 = [vlq.v1n2.csd.value % 7 in [1, 4]]
                    # if fifth in upper parts, compare with pitch of the simultaneous bass note
                    rules3 = [partNumPair[1] != len(score.parts)-1,
                            vlq.v1n2.csd.value % 7 != vertPair[1].objects[-1].csd.value % 7,
                            vlq.v2n2.csd.value % 7 != vertPair[1].objects[-1].csd.value % 7]
                    if not ((all(rules1) and all(rules2)) or (all(rules1) and all(rules3))):
                        error = 'XXX Forbidden similar motion to fifth going into bar ' + str(vlq.v2n2.measureNumber)
                        vlErrors.append(error)
                if isParallelFifth(vlq):
                    error = 'Forbidden parallel motion to fifth going into bar ' + str(vlq.v2n2.measureNumber)
                    vlErrors.append(error)
                if isVoiceCrossing(vlq):
                    # strict rule when the bass is involved
                    if partNumPair[1] == len(score.parts)-1:
                        error = 'Voice crossing with the bass going into bar ' + str(vlq.v2n2.measureNumber)
                        vlErrors.append(error)
                    else:
                        alert = 'ALERT: Upper voices cross going into bar '+ str(vlq.v2n2.measureNumber)
                        vlErrors.append(alert)
                if isVoiceOverlap(vlq):
                    # TODO verify that this rule applies to combined species
                    if partNumPair[1] == len(score.parts)-1:
                        error = 'Voice overlap going into bar ' + str(vlq.v2n2.measureNumber)
                        vlErrors.append(error)
                    else:
                        alert = 'ALERT: Upper voices overlap going into bar ' + str(vlq.v2n2.measureNumber)
                        vlErrors.append(alert)
                if isCrossRelation(vlq):
                    # TODO rewrite in light of Westergaard p. 115
                    # probably need to have access to the species of each line
                    if otherParts == []:
                        error = 'XXX Cross relation going into bar ' + str(vlq.v2n2.measureNumber)
                        vlErrors.append(error)
                    else:
                        # test for step motion in another part
                        crossStep = False
                        for p in otherParts:
                            part = score.parts[p]
                            v3n1 = part.measure(vlq.v1n1.measureNumber).getElementsByClass('Note')[0]
                            v3n2 = part.measure(vlq.v1n2.measureNumber).getElementsByClass('Note')[0]
                            if isDiatonicStep(v3n1, v3n2):
                                crossStep = True
                                break
                        if crossStep == False:
                            error = 'XXX Cross relation going into bar ' + str(vlq.v2n2.measureNumber)
                            vlErrors.append(error)    

            # check oblique motion in second and third species
            # (1) bass is stationary and upper part moves
            rules1 = [vlq.v2n1.offset == vlq.v2n2.offset,
                    vlq.v1n1.offset >= vlq.v2n1.offset,
                    vlq.v1n2.offset > vlq.v2n1.offset] 
            # (2) upper part is stationary and bass part moves
            rules2 = [vlq.v1n1.offset == vlq.v1n2.offset,
                    vlq.v2n1.offset >= vlq.v1n1.offset,
                    vlq.v2n2.offset > vlq.v1n1.offset]
            if all(rules1) or all(rules2): 
                if isVoiceCrossing(vlq):
                    # strict rule when the bass is involved
                    if partNumpair[1] == len(score.parts)-1:
                        error = 'Voice crossing with the bass going into bar ' + str(vlq.v2n2.measureNumber)
                        vlErrors.append(error)
                    else:
                        alert = 'ALERT: Upper voices cross going into bar '+ str(vlq.v2n2.measureNumber)
                        vlErrors.append(alert)

    # check motion downbeat to downbeat
    for vertPair in vertPairsOnbeat:
        # get all the VLQs in these pairs, keyed by partNumPairs
        vlqList = makeVLQsFromVertPair(vertPair, partNumPairs)
        for vlqInstance in vlqList:
            partNumPair = vlqInstance[0]
            vlq = vlqInstance[1]
            otherParts = [p for p in range(0, len(score.parts)) if p not in partNumPair]
            if isParallelUnison(vlq):
                error = 'Forbidden parallel motion to unison going into bar ' + str(vlq.v2n2.measureNumber)
                vlErrors.append(error)    
            if isParallelOctave(vlq):
                error = 'Forbidden parallel motion to octave going into bar ' + str(vlq.v2n2.measureNumber)
                vlErrors.append(error)    
            if isParallelFifth(vlq):
                parDirection = interval.Interval(vlq.v1n1, vlq.v1n2).direction
                if vlq.v1n1.getContextByClass('Part').species == 'second':
                    vSpeciesNote1 = vlq.v1n1
                    vSpeciesNote2 = vlq.v1n2
                    vCantusNote1 = vlq.v2n1
                    vSpeciesPartNum = vlq.v1n1.getContextByClass('Part').partNum
                elif vlq.v1n1.getContextByClass('Part').species == 'second':
                    vSpeciesNote1 = vlq.v2n1
                    vSpeciesNote2 = vlq.v2n2
                    vCantusNote1 = vlq.v1n1
                    vSpeciesPartNum = vlq.v2n1.getContextByClass('Part').partNum
                localNotes = [note for note in score.parts[vSpeciesPartNum].notes if (vSpeciesNote1.index < note.index < vSpeciesNote2.index)]
                # test for step motion contrary to parallels
                rules1 = [vSpeciesNote2.consecutions.leftDirection != parDirection,
                        vSpeciesNote2.consecutions.rightDirection != parDirection,
                        vSpeciesNote2.consecutions.leftType == 'step',
                        vSpeciesNote2.consecutions.leftType == 'step']
                # test for appearance of note as consonance in first bar
                # TODO figure out better way to test for consonance
                rules2 = False
                for note in localNotes:
                    if note.pitch == vSpeciesNote2.pitch and isConsonanceAboveBass(vCantusNote1, note):
                        rules2 == True
                        break
                # TODO verify that the logic of the rules evaluation is correct
                if not (all(rules1) or rules2):
                    error = 'Forbidden parallel motion to pefect fifth from the downbeat of bar ' + \
                        str(vlq.v1n1.measureNumber) + ' to the downbeat of bar ' + str(vlq.v1n2.measureNumber)
                    vlErrors.append(error)
                    
    # Consecutive Verticalities            
    #    on the beat to on the beat (first species)
    #    off the beat to immediately following on the beat
    #    off the beat to immediately following off the beat (third)
    
    # the second pair is coinitiated: onto beat and together onto weak beat
    #    if v1n2.beatStrength == v2n2.beatStrength:
    #    
    
    # the first pair is coinitiated but not the second: on to off beat
    #    if v1n1.beatStrength == v2n1.beatStrength and v1n2.beatStrength > v2n2.beatStrength:
    #    if v1n1.beatStrength == v2n1.beatStrength and v1n2.beatStrength < v2n2.beatStrength:
    # none of the notes is coinitiated: off beat to off beat
    #    if v1n1.beatStrength != v2n1.beatStrength and v1n2.beatStrength != v2n2.beatStrength:
    

    # Nonconsecutive Verticalities
    #    off the beat to next but not immediately following on the beat (third)
    #    off the beat to off the beat in next measure (second, fourth)
    #    on the beat to on the beat (second, third)

                    
    return vlErrors
    
def checkControlOfDissonance(score, analyzer):
    partNumPairs = getAllPartNumPairs(score)
    verts = analyzer.getVerticalities(score)
    bassPartNum = len(score.parts)-1
    for numPair in partNumPairs:
        for vert in verts:
            upperNote = vert.objects[numPair[0]]
            lowerNote = vert.objects[numPair[1]]
            laterNote = None
            if upperNote.beat > lowerNote.beat:
                laterNote = upperNote
            elif upperNote.beat < lowerNote.beat:
                laterNote = lowerNote
            
            # do not evaluate a vertical pair if one note is a rest
            # TODO this is okay for now, but need to check the rules for all gambits
            # ? and what if there's a rest during a line?
            if upperNote.isRest or lowerNote.isRest: continue
            
            # both notes start at the same time, neither is tied over
            rules1 = [upperNote.beat == lowerNote.beat,
                (upperNote.tie == None or upperNote.tie.type == 'start'),
                (lowerNote.tie == None or lowerNote.tie.type == 'start')]
            # the pair constitutes a permissible consonance above the bass
            rules2a = [bassPartNum in numPair,
                isConsonanceAboveBass(lowerNote, upperNote)]
            # the pair constitutes a permissible consonance between upper parts
            rules2b = [bassPartNum not in numPair,
                isConsonanceBetweenUpper(lowerNote, upperNote)]
            # the pair is a permissible dissonance between upper parts
            # TODO this won't work if the bass is a rest and not a note
            rules2c = [bassPartNum not in numPair,
                isPermittedDissonanceBetweenUpper(lowerNote, upperNote),
                isThirdOrSixthAboveBass(vert.objects[bassPartNum], upperNote),
                isThirdOrSixthAboveBass(vert.objects[bassPartNum], lowerNote)]
            
            # test co-initiated simultaneities
            if all(rules1) and not (all(rules2a) or all(rules2b) or all(rules2c)):
                    error = 'Dissonance between co-initiated notes in bar ' + str(upperNote.measureNumber) + \
                        ': ' + str(interval.Interval(lowerNote, upperNote).name)
                    vlErrors.append(error)

            # one note starts after the other
            rules3 = [upperNote.beat != lowerNote.beat, 
                    not (all(rules2a) or all(rules2b) or all(rules2c))]
            rules4 = [upperNote.beat > lowerNote.beat]
            rules5a = [upperNote.consecutions.leftType == 'step',
                    upperNote.consecutions.rightType == 'step']
            rules5b = [lowerNote.consecutions.leftType == 'step',
                    lowerNote.consecutions.rightType == 'step']


            # both notes start at the same time, one of them is tied over
            
#             rules1 = [upperNote.beat == lowerNote.beat,
#                 (upperNote.tie == None or upperNote.tie.type == 'start'),
#                 (lowerNote.tie == None or lowerNote.tie.type == 'start')]
# 
#             if score.parts[-1] in [score.parts[partNum1], score.parts[partNum2]]:
#                 # look for onbeat note that is dissonant and improperly treated
#                 rules = [vPair[speciesPart].beat == 1.0,
#                         not isConsonanceAboveBass(vPair[0], vPair[1]),
#                         not vPair[speciesPart].consecutions.leftType == 'same',
#                         not vPair[speciesPart].consecutions.rightType == 'step']
#                 if all(rules):
#                     error = 'Dissonant interval on the beat that is either not prepared '\
#                             'or not resolved in bar ' + str(vPair[0].measureNumber) + ': '\
#                              + str(interval.Interval(vPair[1], vPair[0]).name)
#                     vlErrors.append(error)
#                 # look for second-species onbeat dissonance
#                 rules = [vPair[speciesPart].beat == 1.0,
#                         vPair[speciesPart].tie == None,
#                         not isConsonanceAboveBass(vPair[0], vPair[1])]
#                 if all(rules):
#                     error = 'Dissonant interval on the beat that is not permitted when ' \
#                             'fourth species is broken in ' + str(vPair[0].measureNumber) + ': ' \
#                              + str(interval.Interval(vPair[1], vPair[0]).name)
#                     vlErrors.append(error)
#                 # look for offbeat note that is dissonant and tied over
#                 rules = [vPair[speciesPart].beat > 1.0,
#                             not isConsonanceAboveBass(vPair[0], vPair[1]),
#                             vPair[0].tie != None or vPair[1].tie != None]
#                 if all(rules):
#                     error = 'Dissonant interval off the beat in bar ' + \
#                             str(vPair[0].measureNumber) + ': ' + \
#                             str(interval.Interval(vPair[1], vPair[0]).name)
#                     vlErrors.append(error)

            # both notes start at the same time, both of them are tied over
            


            if all(rules3) and ((all(rules4) and not all(rules5a)) or (not all(rules4) and not all(rules5b))):
                error = 'Dissonant interval off the beat that is not approached and left by step in bar ' + str(lowerNote.measureNumber) + ': ' + str(interval.Interval(lowerNote, upperNote).name)
                vlErrors.append(error)

        # check whether consecutive dissonances move in one directions
        vlqList = analyzer.getVLQs(score, numPair[0], numPair[1])
        for vlq in vlqList:
#            if vlq.v1n1 == vlq.v1n2 or vlq.v2n1 == vlq.v2n2:
#                print('motion is oblique against sustained tone')
            # either both of the intervals are dissonant above the bass
            rules1a = [bassPartNum in numPair,
                    isVerticalDissonance(vlq.v1n1, vlq.v2n1),
                    isVerticalDissonance(vlq.v1n2, vlq.v2n2)]
            # or both of the intervals are prohibited dissonances between upper parts
            rules1b = [bassPartNum not in numPair,
                    isVerticalDissonance(vlq.v1n1, vlq.v2n1),
                    not isPermittedDissonanceBetweenUpper(vlq.v1n1, vlq.v2n1),
                    isVerticalDissonance(vlq.v1n2, vlq.v2n2),
                    not isPermittedDissonanceBetweenUpper(vlq.v1n2, vlq.v2n2)]
            # either the first voice is stationary and the second voice moves in one direction
            rules2a = [vlq.v1n1 == vlq.v1n2,
                    vlq.v2n1.consecutions.leftDirection == vlq.v2n2.consecutions.leftDirection,
                    vlq.v2n1.consecutions.rightDirection == vlq.v2n2.consecutions.rightDirection]
            # or the second voice is stationary and the first voice moves in one direction
            rules2b = [vlq.v2n1 == vlq.v2n2,
                    vlq.v1n1.consecutions.leftDirection == vlq.v1n2.consecutions.leftDirection,
                    vlq.v1n1.consecutions.rightDirection == vlq.v1n2.consecutions.rightDirection]
            # must be in the same measure
            rules3 = [vlq.v1n1.measureNumber != vlq.v1n2.measureNumber]
            if (all(rules1a) or all(rules1b)) and not (all(rules2a) or all(rules2b)) and not(all(rules3)):
                error = 'Consecutive dissonant intervals in bar ' \
                    + str(vlq.v1n1.measureNumber) + ' are not approached and left '\
                    'in the same direction'
                vlErrors.append(error)

        
    # TODO check third species consecutive dissonances
    
    # TODO fix so that it works with higher species line that start with rests in the bass
    
    # TODO check fourth species control of dissonance
    # check resolution of diss relative to onbeat note (which may move if not whole notes) to determine category of susp
    #     this can be extracted from the vlq: e.g., v1n1,v2n1 and v1n2,v2n1
    # separately check the consonance of the resolution in the vlq (v1n2, v2n2)
    # add rules for multiple parts
    # TODO add contiguous intervals to vlqs ?? xint1, xint2

    pass

def firstSpeciesControlOfDissonance(score, analyzer, partNum1=None, partNum2=None):
    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)
    for vPair in vPairList:
        # check intervals above bass
        if len(score.parts) == partNum2+1:
            if not isConsonanceAboveBass(vPair[0], vPair[1]):
                error = 'Dissonance above bass in bar ' + str(vPair[0].measureNumber) + \
                    ': ' + str(interval.Interval(vPair[1], vPair[0]).simpleName)
                vlErrors.append(error)
        # check intervals between upper voices
        elif len(score.parts) != partNum2+1:
            if not isConsonanceBetweenUpper(vPair[0], vPair[1]):
                error = 'Dissonance between upper parts in bar ' + \
                    str(vPair[0].measureNumber) + ': ' + \
                    str(interval.Interval(vPair[1], vPair[0]).simpleName)
                vlErrors.append(error)
        
def secondSpeciesControlOfDissonance(score, analyzer, partNum1=None, partNum2=None):
    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)
    # NB: parts are numbered top to bottom and vPairs are numbered bottom to top
    if score.parts[partNum1].species == 'second':
        speciesPart = 1 # upper part, hence upper member of vpair
    elif score.parts[partNum2].species == 'second':
        speciesPart = 0 # lower part, hence lower member of vpair
    for vPair in vPairList:
        if vPair != None:
            # evaluate intervals when one of the parts is the bass
            if score.parts[-1] in [score.parts[partNum1], score.parts[partNum2]]:
# TODO vPair[speciesPart] FIX this, speciesPart is not the right index for vPair, also fix in the other species
# how to figure out which member of the vPair is the species line?
# vPairs are numbered bottom to top, parts are numbered top to bottom
                if vPair[speciesPart].beat == 1.0 and not isConsonanceAboveBass(vPair[0], vPair[1]):
                    error = 'Dissonant interval on the beat in bar ' + str(vPair[0].measureNumber) + ': ' + str(interval.Interval(vPair[1], vPair[0]).name)
                    vlErrors.append(error)
                elif vPair[speciesPart].beat > 1.0 and not isConsonanceAboveBass(vPair[0], vPair[1]):
                    rules = [vPair[speciesPart].consecutions.leftType == 'step',
                            vPair[speciesPart].consecutions.rightType == 'step']
                    if not all(rules):
                        error = 'Dissonant interval off the beat that is not approached and left by step in bar ' + str(vPair[0].measureNumber) + ': ' + str(interval.Interval(vPair[1], vPair[0]).name)
                        vlErrors.append(error)

def thirdSpeciesControlOfDissonance(score, analyzer, partNum1=None, partNum2=None):
    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)
    # NB: parts are numbered top to bottom and vPairs are numbered bottom to top
    if score.parts[partNum1].species == 'third':
        speciesPart = partNum2
    elif score.parts[partNum2].species == 'third':
        speciesPart = partNum1
    for vPair in vPairList:
        if vPair != None:
            # evaluate intervals when one of the parts is the bass
            if score.parts[-1] in [score.parts[partNum1], score.parts[partNum2]]:
                if vPair[speciesPart].beat == 1.0 and not isConsonanceAboveBass(vPair[0], vPair[1]):
                    error = 'Dissonant interval on the beat in bar ' + str(vPair[0].measureNumber) + ': ' + str(interval.Interval(vPair[1], vPair[0]).name)
                    vlErrors.append(error)
                elif vPair[speciesPart].beat > 1.0 and not isConsonanceAboveBass(vPair[0], vPair[1]):
                    rules = [vPair[speciesPart].consecutions.leftType == 'step',
                            vPair[speciesPart].consecutions.rightType == 'step']
                    if not all(rules):
                        error = 'Dissonant interval off the beat that is not approached and left by step in bar ' + str(vPair[0].measureNumber) + ': ' + str(interval.Interval(vPair[1], vPair[0]).name)
                        vlErrors.append(error)
    # check consecutive dissonant intervals
    # TODO may have to revise for counterpoint in three or more parts
    vlqList = analyzer.getVLQs(score, partNum1, partNum2)
    for vlq in vlqList:
        rules1 = [isVerticalDissonance(vlq.v1n1, vlq.v2n1),
                isVerticalDissonance(vlq.v1n2, vlq.v2n2)]
        rules2 = [vlq.v1n1 == vlq.v1n2,
                vlq.v2n1.consecutions.leftDirection == vlq.v2n2.consecutions.leftDirection,
                vlq.v2n1.consecutions.rightDirection == vlq.v2n2.consecutions.rightDirection]
        rules3 = [vlq.v2n1 == vlq.v2n2,
                vlq.v1n1.consecutions.leftDirection == vlq.v1n2.consecutions.leftDirection,
                vlq.v1n1.consecutions.rightDirection == vlq.v1n2.consecutions.rightDirection]
        if all(rules1) and not (all(rules2) or all(rules3)):
            error = 'Consecutive dissonant intervals in bar ' \
                + str(vlq.v1n1.measureNumber) + ' are not approached and left '\
                'in the same direction'
            vlErrors.append(error)

def fourthSpeciesControlOfDissonance(score, analyzer, partNum1=None, partNum2=None):
    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)
    # NB: score Parts are numbered top to bottom and vPair parts are numbered bottom to top

    if score.parts[partNum1].species == 'fourth': # species line on top
        speciesPart = 1
    elif score.parts[partNum2].species == 'fourth': # species line on bottom
        speciesPart = 0
    for vPair in vPairList:
        if vPair != None:
            # evaluate on- and offbeat intervals when one of the parts is the bass
            # TODO need to figure out rules for 3 or more parts
            if score.parts[-1] in [score.parts[partNum1], score.parts[partNum2]]:
                # look for onbeat note that is dissonant and improperly treated
                rules = [vPair[speciesPart].beat == 1.0,
                        not isConsonanceAboveBass(vPair[0], vPair[1]),
                        not vPair[speciesPart].consecutions.leftType == 'same',
                        not vPair[speciesPart].consecutions.rightType == 'step']
                if all(rules):
                    error = 'Dissonant interval on the beat that is either not prepared '\
                            'or not resolved in bar ' + str(vPair[0].measureNumber) + ': '\
                             + str(interval.Interval(vPair[1], vPair[0]).name)
                    vlErrors.append(error)
                # look for second-species onbeat dissonance
                rules = [vPair[speciesPart].beat == 1.0,
                        vPair[speciesPart].tie == None,
                        not isConsonanceAboveBass(vPair[0], vPair[1])]
                if all(rules):
                    error = 'Dissonant interval on the beat that is not permitted when ' \
                            'fourth species is broken in ' + str(vPair[0].measureNumber) + ': ' \
                             + str(interval.Interval(vPair[1], vPair[0]).name)
                    vlErrors.append(error)
                # look for offbeat note that is dissonant and tied over
                rules = [vPair[speciesPart].beat > 1.0,
                            not isConsonanceAboveBass(vPair[0], vPair[1]),
                            vPair[0].tie != None or vPair[1].tie != None]
                if all(rules):
                    error = 'Dissonant interval off the beat in bar ' + \
                            str(vPair[0].measureNumber) + ': ' + \
                            str(interval.Interval(vPair[1], vPair[0]).name)
                    vlErrors.append(error)

    # NB: vlq parts and score Parts are numbered top to bottom
    vlqList = analyzer.getVLQs(score, partNum1, partNum2)

    # determine whether breaking of species is permitted
    #     and, if so, whether proper
    breakcount = 0
    earliestBreak = 4
    latestBreak = score.measures - 4
    for vlq in vlqList:
        # look for vlq where second note in species line is not tied over
        if speciesPart == 1: 
            speciesNote = vlq.v1n2
        elif speciesPart == 0:
            speciesNote = vlq.v2n2
        if speciesNote.tie == None and speciesNote.beat > 1.0:
            if allowSecondSpeciesBreak == False and speciesNote.measureNumber != score.measures-1:
                error = 'Breaking of fourth species is allowed only at the end and not in \
                    bars ' + str(speciesNote.measureNumber) + ' to ' + str(speciesNote.measureNumber+1)
                vlErrors.append(error)
            elif allowSecondSpeciesBreak == True and speciesNote.measureNumber != score.measures-1:
                rules = [earliestBreak < speciesNote.measureNumber < latestBreak,
                    breakcount < 1]
                if all(rules):
                    breakcount += 1
                elif breakcount >= 1:
#                    print('no tie in bar', speciesNote.measureNumber)
                    error = 'Breaking of fourth species is only allowed once during the exercise.'
                    vlErrors.append(error)
                elif earliestBreak > speciesNote.measureNumber:
                    error = 'Breaking of fourth species in bars ' + str(speciesNote.measureNumber) + \
                        ' to ' + str(speciesNote.measureNumber+1) + ' occurs too early.'
                    vlErrors.append(error)
                elif speciesNote.measureNumber > latestBreak:
                    error = 'Breaking of fourth species in bars ' + str(speciesNote.measureNumber) + \
                        ' to ' + str(speciesNote.measureNumber+1) + ' occurs too late.'
                    vlErrors.append(error)
                # if the first vInt is dissonant, the speciesNote will be checked later
                # if the first vInt is consonant, the speciesNote might be dissonant
                rules = [not isVerticalDissonance(vlq.v1n1, vlq.v2n1),
                        isVerticalDissonance(vlq.v1n2, vlq.v2n2),
                        speciesNote.consecutions.leftType == 'step',
                        speciesNote.consecutions.rightType == 'step']
                if not all(rules):
                    error = 'Dissonance off the beat in bar ' + str(speciesNote.measureNumber) + \
                            ' is not approached and left by step.'
                    vlErrors.append(error)    

    # Westergaard lists
    strongSuspensions = {'upper': ['d7-6', 'm7-6', 'M7-6'], 
                        'lower': ['m2-3', 'M2-3', 'A2-3']}
    intermediateSuspensions = {'upper': ['m9-8', 'M9-8', 'd4-3', 'P4-3', 'A4-3'], 
                        'lower': ['A4-5', 'd5-6', 'A5-6']}
    weakSuspensions = {'upper': ['m2-1', 'M2-1'], 
                        'lower': [ 'm7-8', 'M7-8', 'P4-5']}
    # list of dissonances inferred from Westergaard lists
    validDissonances = ['m2', 'M2', 'A2', 'd4', 'P4', 'A5', 'd5', 'A5', 'm7', 'd7', 'M7']

    # function for distinguishing between intervals 9 and 2 in upper lines
    def dissName(intval):
        if intval.simpleName in ['m2', 'M2', 'A2'] and intval.name not in ['m2', 'M2', 'A2']:
            intervalName = interval.add([intval.simpleName, 'P8']).name
        else:
            intervalName = intval.simpleName
        return intervalName

    # make list of dissonant syncopes        
    syncopeList = {}
    for vlq in vlqList:
        if speciesPart == 1: # species line on top
            if vlq.v1n1.tie:
                if vlq.v1n1.tie.type == 'stop':
                    if vlq.vIntervals[0].simpleName in validDissonances:
                        syncopeList[vlq.v1n1.measureNumber] = (dissName(vlq.vIntervals[0]) + '-' + vlq.vIntervals[1].semiSimpleName[-1])
        elif speciesPart == 0: # species line on bottom
            if vlq.v2n1.tie:
                if vlq.v2n1.tie.type == 'stop':
                    if vlq.vIntervals[0].simpleName in validDissonances:
                        syncopeList[vlq.v2n1.measureNumber] = (vlq.vIntervals[0].simpleName + '-' + vlq.vIntervals[1].semiSimpleName[-1])
    if speciesPart == 1:
        for bar in syncopeList:
            if syncopeList[bar] not in strongSuspensions['upper'] and syncopeList[bar] not in  intermediateSuspensions['upper']:
                error = 'The dissonant syncopation in bar '+ str(bar) + ' is not permitted: ' + str(syncopeList[bar])
                vlErrors.append(error)
    elif speciesPart == 0:
        for bar in syncopeList:
            if syncopeList[bar] not in strongSuspensions['lower'] and syncopeList[bar] not in  intermediateSuspensions['lower']:
                error = 'The dissonant syncopation in bar ' + str(bar) + ' is not permitted: ' + str(syncopeList[bar])
                vlErrors.append(error)

def forbiddenMotionsOntoBeatWithoutSyncope(score, vlq, partNum1, partNum2):
    vlqBassNote = score.parts[-1].measure(vlq.v1n2.measureNumber).getElementsByClass('Note')[0]
    if isSimilarUnison(vlq):
        error = 'Forbidden similar motion to unison going into bar ' + str(vlq.v2n2.measureNumber)
        vlErrors.append(error)
    if isSimilarFromUnison(vlq):
        error = 'Forbidden similar motion from unison in bar ' + str(vlq.v2n1.measureNumber)
        vlErrors.append(error)
    if isSimilarOctave(vlq):
        rules = [vlq.hIntervals[0].name in ['m2', 'M2'],
                vlq.v1n2.csd.value % 7 == 0,
                vlq.v1n2.measureNumber == score.measures,
                vlq.v2n2.measureNumber == score.measures]
        if not all(rules):
            error = 'Forbidden similar motion to octave going into bar ' + str(vlq.v2n2.measureNumber)
            vlErrors.append(error)
    if isSimilarFifth(vlq):
        rules1 = [vlq.hIntervals[0].name in ['m2', 'M2']]
        rules2 = [vlq.v1n2.csd.value % 7 in [1, 4]]
        # if fifth in upper parts, compare with pitch of the simultaneous bass note
        rules3 = [partNum1 != len(score.parts)-1,
                partNum2 != len(score.parts)-1,
                vlq.v1n2.csd.value % 7 != vlqBassNote.csd.value % 7,
                vlq.v2n2.csd.value % 7 != vlqBassNote.csd.value % 7]
        # TODO recheck the logic of this
        if not ((all(rules1) and all(rules2)) or (all(rules1) and all(rules3))):
            error = 'Forbidden similar motion to fifth going into bar ' + str(vlq.v2n2.measureNumber)
            vlErrors.append(error)
    if isParallelUnison(vlq):
        error = 'Forbidden parallel motion to unison going into bar ' + + str(vlq.v2n2.measureNumber)
        vlErrors.append(error)
    if isParallelOctave(vlq):
        error = 'Forbidden parallel motion to octave going into bar ' + str(vlq.v2n2.measureNumber)
        vlErrors.append(error)
    if isParallelFifth(vlq):
        error = 'Forbidden parallel motion to fifth going into bar ' + str(vlq.v2n2.measureNumber)
        vlErrors.append(error)
    if isVoiceCrossing(vlq):
        # strict rule when the bass is involved
        if partNum1 == len(score.parts)-1 or partNum2 == len(score.parts)-1:
            error = 'Voice crossing going into bar ' + str(vlq.v2n2.measureNumber)
            vlErrors.append(error)
        else:
            alert = 'ALERT: Upper voices cross going into bar '+ str(vlq.v2n2.measureNumber)
            vlErrors.append(alert)
    if isVoiceOverlap(vlq):
        if partNum1 == len(score.parts)-1 or partNum2 == len(score.parts)-1:
            error = 'Voice overlap going into bar ' + str(vlq.v2n2.measureNumber)
            vlErrors.append(error)
        else:
            alert = 'ALERT: Upper voices overlap going into bar ' + str(vlq.v2n2.measureNumber)
            vlErrors.append(alert)
    if isCrossRelation(vlq):
        if len(score.parts) < 3:
            error = 'Cross relation going into bar ' + str(vlq.v2n2.measureNumber)
            vlErrors.append(error)
        else:
            # test for step motion in another part
            crossStep = False
            for part in score.parts:
                if part != score.parts[partNum1] and part != score.parts[partNum2]:
                    vlqOtherNote1 = part.measure(vlq.v1n1.measureNumber).getElementsByClass('Note')[0]
                    vlqOtherNote2 = part.measure(vlq.v1n2.measureNumber).getElementsByClass('Note')[0]
                    if vlqOtherNote1.csd.value - vlqOtherNote2.csd.value == 1:
                        crossStep = True
                        break
            if crossStep == False:
                error = 'Cross relation going into bar ' + str(vlq.v2n2.measureNumber)
                vlErrors.append(error)    

def firstSpeciesForbiddenMotions(score, analyzer, partNum1=None, partNum2=None):
#    if partNum1 == None and partNum2 == None:
    vlqList = analyzer.getVLQs(score, partNum1, partNum2)
    for vlq in vlqList:
        forbiddenMotionsOntoBeatWithoutSyncope(score, vlq, partNum1, partNum2)

def secondSpeciesForbiddenMotions(score, analyzer, partNum1=None, partNum2=None):
#    if partNum1 == None and partNum2 == None:

    # check motion across the barline
    vlqList = analyzer.getVLQs(score, partNum1, partNum2)
    for vlq in vlqList:
        forbiddenMotionsOntoBeatWithoutSyncope(score, vlq, partNum1, partNum2)

    # check motion from beat to beat
    vlqOnbeatList = analyzer.getOnbeatVLQs(score, partNum1, partNum2)
    for vlq in vlqOnbeatList:
        if isParallelUnison(vlq):
            error = 'Forbidden parallel motion to unison from bar ' + \
                str(vlq.v1n1.measureNumber) + ' to bar ' + str(vlq.v1n2.measureNumber)
            vlErrors.append(error)
        # TODO revise for three parts, Westergaard p. 143
        # requires looking at simultaneous VLQs in a pair of verticalities
        if isParallelOctave(vlq):
            error = 'Forbidden parallel motion to octave from bar ' + \
                str(vlq.v1n1.measureNumber) + ' to bar ' + str(vlq.v1n2.measureNumber)
            vlErrors.append(error)            
        if isParallelFifth(vlq):
            parDirection = interval.Interval(vlq.v1n1, vlq.v1n2).direction
            if vlq.v1n1.getContextByClass('Part').species == 'second':
                vSpeciesNote1 = vlq.v1n1
                vSpeciesNote2 = vlq.v1n2
                vCantusNote1 = vlq.v2n1
                vSpeciesPartNum = vlq.v1n1.getContextByClass('Part').partNum
            elif vlq.v1n1.getContextByClass('Part').species == 'second':
                vSpeciesNote1 = vlq.v2n1
                vSpeciesNote2 = vlq.v2n2
                vCantusNote1 = vlq.v1n1
                vSpeciesPartNum = vlq.v2n1.getContextByClass('Part').partNum
            localNotes = [note for note in score.parts[vSpeciesPartNum].notes if (vSpeciesNote1.index < note.index < vSpeciesNote2.index)]
            # test for step motion contrary to parallels
            rules1 = [vSpeciesNote2.consecutions.leftDirection != parDirection,
                    vSpeciesNote2.consecutions.rightDirection != parDirection,
                    vSpeciesNote2.consecutions.leftType == 'step',
                    vSpeciesNote2.consecutions.leftType == 'step']
            # test for appearance of note as consonance in first bar
            # TODO figure out better way to test for consonance
            rules2 = False
            for note in localNotes:
                if note.pitch == vSpeciesNote2.pitch and isConsonanceAboveBass(vCantusNote1, note):
                    rules2 == True
                    break
            # TODO verify that the logic of the rules evaluation is correct
            if not (all(rules1) or rules2):
                error = 'Forbidden parallel motion to pefect fifth from the downbeat of bar ' + \
                    str(vlq.v1n1.measureNumber) + ' to the downbeat of bar ' + str(vlq.v1n2.measureNumber)
                vlErrors.append(error)

def thirdSpeciesForbiddenMotions(score, analyzer, partNum1=None, partNum2=None):
    # TODO: finish this script??
    
    def checkMotionsOntoBeat():
    # check motion across the barline
        vlqList = analyzer.getVLQs(score, partNum1, partNum2)
        for vlq in vlqList:
            # check motion across the barline, as in first and second species
            if vlq.v1n2.beat == 1.0 and vlq.v2n2.beat == 1.0:
                forbiddenMotionsOntoBeatWithoutSyncope(score, vlq, partNum1, partNum2)
            else:
            # check motion within the bar
                if isVoiceCrossing(vlq):
                # strict rule when the bass is involved
                    if partNum1 == len(score.parts)-1 or partNum2 == len(score.parts)-1:
                        error = 'Voice crossing in bar ' + str(vlq.v2n2.measureNumber)
                        vlErrors.append(error)
                    else:
                        alert = 'ALERT: Upper voices cross in bar '+ str(vlq.v2n2.measureNumber)
                        vlErrors.append(alert)

    def checkMotionsBeatToBeat():
    # check motion from beat to beat
        vlqOnbeatList = analyzer.getOnbeatVLQs(score, partNum1, partNum2)
        for vlq in vlqOnbeatList:
            if isParallelUnison(vlq):
                error = 'Forbidden parallel motion to unison from bar ' + \
                    str(vlq.v1n1.measureNumber) + ' to bar ' + str(vlq.v1n2.measureNumber)
                vlErrors.append(error)
            if isParallelOctave(vlq) or isParallelFifth(vlq):
                parDirection = interval.Interval(vlq.v1n1, vlq.v1n2).direction
                if vlq.v1n1.getContextByClass('Part').species == 'third':
                    vSpeciesNote1 = vlq.v1n1
                    vSpeciesNote2 = vlq.v1n2
                    vCantusNote1 = vlq.v2n1
                    vSpeciesPartNum = vlq.v1n1.getContextByClass('Part').partNum
                elif vlq.v2n1.getContextByClass('Part').species == 'third':
                    vSpeciesNote1 = vlq.v2n1
                    vSpeciesNote2 = vlq.v2n2
                    vCantusNote1 = vlq.v1n1
                    vSpeciesPartNum = vlq.v2n1.getContextByClass('Part').partNum
                localSpeciesMeasure = score.parts[vSpeciesPartNum].measures(vCantusNote1.measureNumber, vCantusNote1.measureNumber)
                localNotes = localSpeciesMeasure.getElementsByClass('Measure')[0].notes
                localNotes = [note for note in localNotes if (vSpeciesNote1.index < note.index < vSpeciesNote2.index)]
                # test for step motion contrary to parallels
                rules1 = [vSpeciesNote2.consecutions.leftDirection != parDirection,
                        vSpeciesNote2.consecutions.rightDirection != parDirection,
                        vSpeciesNote2.consecutions.leftType == 'step',
                        vSpeciesNote2.consecutions.leftType == 'step']
                # test for appearance of note as consonance in first bar
                # TODO figure out better way to test for consonance
                rules2 = False
                for note in localNotes:
                    if note.pitch == vSpeciesNote2.pitch and isConsonanceAboveBass(vCantusNote1, note):
                        rules2 = True
                        break
                # TODO verify that the logic of the rules evaluation is correct
                if not (all(rules1) or rules2):
                    error = 'Forbidden parallel motion from the downbeat of bar ' + \
                        str(vlq.v1n1.measureNumber) + ' to the downbeat of bar ' + str(vlq.v1n2.measureNumber)
                    vlErrors.append(error)

    def checkMotionsOffToOnBeat():
    # check motions from off to nonconsecutive onbeat
        vlqNonconsecutivesList = analyzer.getNonconsecutiveOffbeatToOnbeatVLQs(score, partNum1, partNum2)
        for vlq in vlqNonconsecutivesList:
            if isParallelUnison(vlq):
                error = 'Forbidden parallel motion to unison from bar ' + \
                    str(vlq.v1n1.measureNumber) + ' to bar ' + str(vlq.v1n2.measureNumber)
                vlErrors.append(error)
            if isParallelOctave(vlq):
                parDirection = interval.Interval(vlq.v1n1, vlq.v1n2).direction
                if vlq.v1n1.getContextByClass('Part').species == 'third':
                    vSpeciesNote1 = vlq.v1n1
                    vSpeciesNote2 = vlq.v1n2
                    vCantusNote1 = vlq.v2n1
                    vSpeciesPartNum = vlq.v1n1.getContextByClass('Part').partNum
                elif vlq.v1n1.getContextByClass('Part').species == 'third':
                    vSpeciesNote1 = vlq.v2n1
                    vSpeciesNote2 = vlq.v2n2
                    vCantusNote1 = vlq.v1n1
                    vSpeciesPartNum = vlq.v2n1.getContextByClass('Part').partNum
                # make a list of notes in the species line simultaneous with the first cantus tone
                localSpeciesMeasure = score.parts[vSpeciesPartNum].measures(vCantusNote1.measureNumber, vCantusNote1.measureNumber)
                localNotes = localSpeciesMeasure.getElementsByClass('Measure')[0].notes
                localNotes = [note for note in localNotes]
                # test for step motion contrary to parallels
                rules1 = [vSpeciesNote2.consecutions.leftDirection != parDirection,
                        vSpeciesNote2.consecutions.rightDirection != parDirection,
                        vSpeciesNote2.consecutions.leftType == 'step',
                        vSpeciesNote2.consecutions.leftType == 'step']
                # test for appearance of note as consonance in first bar
                # TODO figure out better way to test for consonance
                rules2 = False
                for note in localNotes:
                    if note.pitch == vSpeciesNote2.pitch and isConsonanceAboveBass(vCantusNote1, note):
                        rules2 = True
                        break
                if not (all(rules1) or rules2):
                    error = 'Forbidden parallel octaves from an offbeat note in bar ' + \
                        str(vlq.v1n1.measureNumber) + ' to the downbeat of bar ' + str(vlq.v1n2.measureNumber)
                    vlErrors.append(error)
    # check leaps of a fourth in the bass: function called in checkCounterpoint()
    
    checkMotionsOntoBeat()
    checkMotionsBeatToBeat()
    checkMotionsOffToOnBeat()

#    print('NOTICE: Forbidden forms of motion in third species have not been thoroughly checked!')
    pass

def fourthSpeciesForbiddenMotions(score, analyzer, partNum1=None, partNum2=None):
    vlqList = analyzer.getVLQs(score, partNum1, partNum2)

    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)
    # NB: score Parts are numbered top to bottom and vPair parts are numbered bottom to top
    if score.parts[partNum1].species == 'fourth': # species line on top
        speciesPart = 1
    elif score.parts[partNum2].species == 'fourth': # species line on bottom
        speciesPart = 0
    vPairsOnbeat = []
    vPairsOnbeatDict = {}
    vPairsOffbeat = []
    for vPair in vPairList:
        if vPair != None:
            # evaluate offbeat intervals when one of the parts is the bass
            if vPair[speciesPart].beat == 1.0:
                vPairsOnbeat.append(vPair)
                vPairsOnbeatDict[vPair[speciesPart].measureNumber] = vPair
            else:
                vPairsOffbeat.append(vPair)
    vlqsOffbeat = makeVLQFromVPair(vPairsOffbeat)
    vlqsOnbeat = makeVLQFromVPair(vPairsOnbeat)
    for vlq in vlqsOffbeat:
        if isParallelUnison(vlq):
            error = 'Forbidden parallel motion to unison going into bar ' + str(vlq.v2n2.measureNumber)
            vlErrors.append(error)
        if isParallelOctave(vlq):
            thisBar = vlq.v1n2.measureNumber
            thisOnbeatPair = vPairsOnbeatDict[thisBar]
            if not isConsonanceAboveBass(thisOnbeatPair[0], thisOnbeatPair[1]):
                error = 'Forbidden parallel motion to octave going into bar ' + str(vlq.v2n2.measureNumber)
                vlErrors.append(error)
    for vlq in vlqsOnbeat:
        if isParallelUnison(vlq):
            error = 'Forbidden parallel motion to unison going into bar ' + str(vlq.v2n2.measureNumber)
            vlErrors.append(error)        
    # check second-species motion across barlines, looking at vlq with initial untied offbeat note
    for vlq in vlqList:
        if speciesPart == 1: 
            speciesNote = vlq.v1n1
        elif speciesPart == 0:
            speciesNote = vlq.v2n1
        if speciesNote.tie == None and speciesNote.beat > 1.0:
            forbiddenMotionsOntoBeatWithoutSyncope(score, vlq, partNum1, partNum2)    

def checkSecondSpeciesNonconsecutiveUnisons(score, analyzer, partNum1=None, partNum2=None):
    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)
    # NB: parts are numbered top to bottom and vPairs are numbered bottom to top
    if score.parts[partNum1].species == 'second':
        speciesPart = 1
    elif score.parts[partNum2].species == 'second':
        speciesPart = 0
    else:#neither part is second species
        return
    firstUnison = None
    for vPair in vPairList:
        if firstUnison:
            if (interval.Interval(vPair[0], vPair[1]).name == 'P1'
                    and vPair[speciesPart].beat == 1.5
                    and vPair[speciesPart].measureNumber -1 == firstUnison[0]):
#                if vPair[speciesPart].consecutions.leftDirection == firstUnison[1][speciesPart].consecutions.leftDirection:
                error = 'Offbeat unisons in bars ' +  str(firstUnison[0]) + ' and ' + str(vPair[speciesPart].measureNumber)
                vlErrors.append(error)
        if vPair != None:
            if (interval.Interval(vPair[0], vPair[1]).name == 'P1'
                    and vPair[speciesPart].beat > 1.0):
                firstUnison = (vPair[speciesPart].measureNumber, vPair)
    
def checkSecondSpeciesNonconsecutiveOctaves(score, analyzer, partNum1=None, partNum2=None):
    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)
    # NB: parts are numbered top to bottom and vPairs are numbered bottom to top
    if score.parts[partNum1].species == 'second':
        speciesPart = 1
    elif score.parts[partNum2].species == 'second':
        speciesPart = 0
    else:#neither part is second species
        return
    firstOctave = None
    for vPair in vPairList:
        if firstOctave:
            if (interval.Interval(vPair[0], vPair[1]).name == 'P8'
                    and vPair[speciesPart].beat > 1.0
                    and vPair[speciesPart].measureNumber-1 == firstOctave[0]):
                if interval.Interval(firstOctave[1][speciesPart], vPair[speciesPart]).isDiatonicStep:
                    if vPair[speciesPart].consecutions.leftDirection == firstOctave[1][speciesPart].consecutions.leftDirection:
                        error = 'Offbeat octaves in bars ' + str(firstOctave[0]) + ' and ' + str(vPair[speciesPart].measureNumber)
                        vlErrors.append(error)
                elif interval.Interval(firstOctave[1][speciesPart], vPair[speciesPart]).generic.isSkip:
                    if (vPair[speciesPart].consecutions.leftDirection != firstOctave[1][speciesPart].consecutions.leftDirection
                            or firstOctave[1][speciesPart].consecutions.rightInterval.isDiatonicStep):
                        continue
                    else:
                        error = 'Offbeat octaves in bars ' + str(firstOctave[0]) + ' and ' + str(vPair[speciesPart].measureNumber)
                        vlErrors.append(error)
        if vPair != None:
            if (interval.Interval(vPair[0], vPair[1]).name == 'P8'
                    and vPair[speciesPart].beat == 1.5):
                firstOctave = (vPair[speciesPart].measureNumber, vPair)

def checkFourthLeapsInBass(score, analyzer):
    analyzer.identifyFourthLeapsInBass(score)
    bassFourthsList = analyzer.store[score.id]['ResultDict']['fourthLeapsBass']
    for bassFourth in bassFourthsList:
        bn1 = bassFourth.nnls.objectList[0]
        bn2 = bassFourth.nnls.objectList[1]
        bnPartNum = len(score.parts)-1
        bn1Meas = bn1.measureNumber
        bn2Meas = bn2.measureNumber
        bn1Start = bn1.offset
        bn2Start = bn2.offset
        bn1End = bn1Start + bn1.quarterLength
        bn2End = bn2Start + bn2.quarterLength
        # implication is true until proven otherwise
        impliedSixFour = True
                
        # leaps of a fourth within a measure 
        if bn1Meas == bn2Meas: 
            fourthBass = interval.getAbsoluteLowerNote(bn1, bn2)
            for n in score.parts[bnPartNum].measure(bn1Meas).notes:
                rules1 = [n != bn1,
                            n != bn2,
                            n == interval.getAbsoluteLowerNote(n, fourthBass),
                            interval.Interval(n, fourthBass).semitones < interval.Interval('P8').semitones,
                            isTriadicConsonance(n, bn1),
                            isTriadicConsonance(n, bn2)]
                if all(rules1):
                    impliedSixFour = False
                    break

        # leaps of a fourth across the barline
        elif bn1Meas == bn2Meas-1:
            # check upper parts for note that denies the implication
            for part in score.parts[0:bnPartNum]:
                # get the two bars in the context of the bass fourth
                bars = part.getElementsByOffset(offsetStart=bn1Start,
                                offsetEnd=bn2End,
                                includeEndBoundary=False,
                                mustFinishInSpan=False,
                                mustBeginInSpan=False,
                                includeElementsThatEndAtStart=False,
                                classList=None)
                # make note list for each bar of the part, simultaneous with notes of the fourth
                barseg1 = []
                barseg2 = []
                for bar in bars: 
                    # bar notes 1
                    barns1 = bar.getElementsByOffset(offsetStart=bn1Start-bar.offset,
                                    offsetEnd=bn1End-bar.offset,
                                    includeEndBoundary=False,
                                    mustFinishInSpan=False,
                                    mustBeginInSpan=False,
                                    includeElementsThatEndAtStart=False,
                                    classList='Note')
                    for n in barns1:
                        barseg1.append(n)
                    # bar notes 2
                    barns2 = bar.getElementsByOffset(offsetStart=bn2Start-bar.offset,
                                    offsetEnd=bn2End,
                                    includeEndBoundary=False,
                                    mustFinishInSpan=False,
                                    mustBeginInSpan=False,
                                    includeElementsThatEndAtStart=False,
                                    classList='Note')
                    for n in barns2:
                        barseg2.append(n)

                for n in barseg1:
                    # rules for all species
                    # locally consonant, step-class contiguity
                    rules1 = [isConsonanceAboveBass(bn1, n),
                            interval.Interval(bn2, n).simpleName in ['m2', 'M2', 'm7', 'M7']]

                    # rules for first species
                    if len(barseg1) == 1:
                        if all(rules1):
                            impliedSixFour = False
                            break

                    # rules for second species
                    elif len(barseg1) == 2 and not barseg1[0].tie:
                        # first in bar, leapt to, or last in bar (hence contiguous with bn2)
                        rules2 = [n.offset == 0.0,
                                n.consecutions.leftType == 'skip',
                                n.offset+n.quarterLength == score.measure(bn1Meas).quarterLength]
                        if all(rules1) and any(rules2):
                            impliedSixFour = False
                            break

                    # rules for third species
                    elif len(barseg1) > 2:
                        # first in bar or last in bar (hence contiguous with bn2)
                        rules3a = [n.offset == 0.0,
                                n.offset+n.quarterLength == score.measure(bn1Meas).quarterLength]
                        # not first or last in bar and no step follows
                        stepfollows = [x for x in barseg1 if x.offset > n.offset and isConsonanceAboveBass(bn1, x) and isDiatonicStep(x, n)]
                        rules3b = [n.offset > 0.0,
                                n.offset+n.quarterLength < score.measure(bn1Meas).quarterLength,
                                stepfollows == []]

                        if all(rules1) and (any(rules3a) or all(rules3b)):
                            impliedSixFour = False
                            break

                    # rules for fourth species
                    elif len(barseg1) == 2 and barseg1[0].tie:
                        rules4 = [n.tie.type == 'start']
                        if all(rules1) and all(rules4):
                            impliedSixFour = False
                            break

                for n in barseg2:
                    # locally consonant, step-class contiguity
                    rules1 = [isConsonanceAboveBass(bn2, n),
                            interval.Interval(bn1, n).simpleName in ['m2', 'M2', 'm7', 'M7']]

                    # rules for first species
                    if len(barseg2) == 1:
                        if all(rules1):
                            impliedSixFour = False
                            break

                    # rules for second species
                    elif len(barseg2) == 2 and not barseg2[0].tie:
                        rules2 = [n.offset == 0.0,
                                n.consecutions.leftType == 'skip']
                        if all(rules1) and any(rules2):
                            impliedSixFour = False
                            break

                    # rules for third species
                    elif len(barseg2) > 2:
                        # first in bar or not preceded by cons a step away
                        stepprecedes = [x for x in barseg2 if x.offset < n.offset and isConsonanceAboveBass(bn1, x) and isDiatonicStep(x, n)]
                        rules3 = [n.offset == 0.0, 
                                stepprecedes == []]
                        if all(rules1) and any(rules3):
                            impliedSixFour = False
                            break

                    # rules for fourth species
                    elif len(barseg2) == 2 and barseg2[0].tie:
                        # TODO verify that no additional rule is needed
                        rules4 = []#[n.tie.type == 'start']
                        if all(rules1) and all(rules4):
                            impliedSixFour = False
                            break
            # check third species bass part for note that denies the implication
            if score.parts[bnPartNum].species == 'third':
                bn1Measure = bn1.measureNumber
                # get the notes in the bar of the first bass note
                bassnotes = score.parts[bnPartNum].flat.notes
                barns1 = [n for n in bassnotes if n.measureNumber == bn1Measure]
                
                # TODO finish this test
                for n in barns1:
                    rules3a = [isDiatonicStep(n, bn2)]
                    rules3b = [n.offset == 0.0,
                            n == barns1[-2]]
                    if all(rules3a) and any(rules3b):
                        impliedSixFour = False
                        break    

        if impliedSixFour == True and bn1Meas == bn2Meas:
            error = 'Prohibited leap of a fourth in bar ' + str(bn1Meas)
            vlErrors.append(error)
        elif impliedSixFour == True and bn1Meas != bn2Meas:
            error = 'Prohibited leap of a fourth in bars ' + str(bn1Meas) +  ' to ' + str(bn2Meas)
            vlErrors.append(error)
#        return impliedSixFour




def makeVLQFromVPair(vPairList):
#    a, b = itertools.tee(vPairList)
#    next(b, None)
#    zipped = zip(a, b)
    quartetList = []
#    for quartet in list(zipped):
    for quartet in pairwise(vPairList):
        quartetList.append((quartet[0][1],quartet[1][1],quartet[0][0],quartet[1][0]))
    vlqList = []
    for quartet in quartetList:
        vlqList.append(voiceLeading.VoiceLeadingQuartet(quartet[0], quartet[1], quartet[2], quartet[3]))
    return vlqList

def makeVLQsFromVertPair(vertPair, partNumPairs):
    # given a pair of verticalities and a list of component part pairing,
    # construct all the VLQs among notes
    vlqList = []
    for numPair in partNumPairs:
        upperPart = numPair[0]
        lowerPart = numPair[1]
        v1n1 = vertPair[0].objects[upperPart]
        v1n2 = vertPair[1].objects[upperPart]
        v2n1 = vertPair[0].objects[lowerPart]
        v2n2 = vertPair[1].objects[lowerPart]
        # do not make a VLQ if one note is a rest
        if v1n1.isRest or v1n2.isRest or v2n1.isRest or v2n2.isRest:
            continue
        else:
            vlqList.append((numPair, voiceLeading.VoiceLeadingQuartet(v1n1, v1n2, v2n1, v2n2)))
    return vlqList        

def pairwise(span):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(span)
    next(b, None)
    zipped = zip(a, b)
    return list(zipped)

def pairwiseFromLists(list1, list2):
    'return pairwise permutations from two lists'
    comb = [(i,j) for i in list1 for j in list2]
    result = []
    for c in comb:
        if c[0] < c[1]:
            result.append(c)
        else:
            result.append((c[1],c[0]))
    return result

def pairwiseFromList(list1):
    'return pairwise combinations from one list'
    comb = list(itertools.combinations(list1, 2))
    return comb

# LIBRARY OF METHODS FOR EVALUTING VOICE LEADING ATOMS

# Methods for note pairs

def isConsonanceAboveBass(b, u):
    # equivalent to music21.Interval.isConsonant()
    # input two notes with pitch, a bass note an upper note
    vert_int = interval.Interval(b, u)
    if interval.getAbsoluteLowerNote(b, u) == b and vert_int.simpleName in {'P1', 'm3', 'M3', 'P5', 'm6', 'M6'}:
        return True
    else: return False

def isThirdOrSixthAboveBass(b, u):
    # input two notes with pitch, a bass note an upper note
    vert_int = interval.Interval(b, u)
    if interval.getAbsoluteLowerNote(b, u) == b and vert_int.simpleName in {'m3', 'M3', 'm6', 'M6'}:
        return True
    else: return False

def isConsonanceBetweenUpper(u1, u2):
    # input two notes with pitch, two upper-line notes
    # P4, A4, and d5 require additional test with bass: isPermittedDissonanceBetweenUpper()
    vert_int = interval.Interval(u1, u2)
    if vert_int.simpleName in {'P1', 'm3', 'M3', 'P4', 'P5', 'm6', 'M6'}:
        return True
    else: return False
    
def isPermittedDissonanceBetweenUpper(u1, u2):
    # input two notes with pitch, two upper-line notes
    # P4, A4, and d5 require additional test with bass
    vert_int = interval.Interval(u1, u2)
    if vert_int.simpleName in {'P4', 'A4', 'd5'}:
        return True
    else: return False
    
def isTriadicConsonance(n1, n2):
    int = interval.Interval(n1, n2)
    if int.simpleName in {'P1', 'm3', 'M3', 'P4', 'P5', 'm6', 'M6'}:
        return True
    else: return False

def isTriadicInterval(n1, n2):
    ivl = interval.Interval(n1, n2)
    if ivl.simpleName in {'P1', 'm3', 'M3', 'P4', 'A4', 'd5', 'P5', 'm6', 'M6'}:
        return True
    else: return False

def isPerfectVerticalConsonance(n1, n2):
    ivl = interval.Interval(n1, n2)
    if ivl.simpleName in {'P1', 'P5', 'P8'}:
        return True
    else: return False

def isImperfectVerticalConsonance(n1, n2):
    ivl = interval.Interval(n1, n2)
    if ivl.simpleName in {'m3', 'M3', 'm6', 'M6'}:
        return True
    else: return False

def isVerticalDissonance(n1, n2):
    ivl = interval.Interval(n1, n2)
    if ivl.simpleName not in {'P1', 'P5', 'P8', 'm3', 'M3', 'm6', 'M6'}:
        return True
    else: return False

def isDiatonicStep(n1, n2):
    lin_ivl = interval.Interval(n1, n2)
    if lin_ivl.name in {'m2', 'M2'}:
        return True
    else: return False
    
def isUnison(n1, n2):
    lin_ivl = interval.Interval(n1, n2)
    if lin_ivl.name in {'P1'}:
        return True
    else: return False

def isOctave(n1, n2):
    lin_ivl = interval.Interval(n1, n2)
    if lin_ivl.name in {'P8', 'P15'}:
        return True
    else: return False
        

# Methods for verticalities

def isConsonantSonority(verticality):
    """for checking onbeat sonorities, accepts a verticality of Notes"""
    pass
    # TODO write the function
#     v1 = verticality.removeRedundantPitchNames(inPlace=False)
#     if len(v1.pitches) == 1:
#         return True
#     elif len(v1.pitches) == 2:
#         v2 = verticality.closedPosition()
#         # to get from lowest to highest for P4 protection
#         v3 = v2.removeRedundantPitches(inPlace=False)
#         i = interval.notesToInterval(v3.pitches[0], v3.pitches[1])
#         return i.isConsonant()
#     elif len(v1.pitches) == 3:
#         if ((verticality.isMajorTriad() is True or verticality.isMinorTriad() is True)
#                 and (verticality.inversion() != 2)):
#             return True
#         elif (verticality.isDiminishedTriad() is True and verticality.inversion == 1)
#             return True
#         else:
#             return False
#     else:
#         return False
    

# Methods for voice-leading quartets

def isSimilarUnison(vlq):
    rules = [vlq.similarMotion() == True,
            vlq.vIntervals[1] != vlq.vIntervals[0],
            vlq.vIntervals[1].name == 'P1']
    if all(rules):
        return True
    else: return False

def isSimilarFromUnison(vlq):
    rules = [vlq.similarMotion() == True,
            vlq.vIntervals[1] != vlq.vIntervals[0],
            vlq.vIntervals[0].name == 'P1']
    if all(rules):
        return True
    else: return False

def isSimilarFifth(vlq):
    rules = [vlq.similarMotion() == True,
            vlq.vIntervals[1] != vlq.vIntervals[0],
            vlq.vIntervals[1].simpleName == 'P5']
    if all(rules):
        return True
    else: return False
                
def isSimilarOctave(vlq):
    rules = [vlq.similarMotion() == True,
            vlq.vIntervals[1] != vlq.vIntervals[0],
            vlq.vIntervals[1].name in ['P8', 'P15', 'P22']]
    if all(rules):
        return True
    else: return False
    
def isParallelUnison(vlq):
    rules = [vlq.parallelMotion() == True,
            vlq.vIntervals[1].name in ['P1']]
    if all(rules):
        return True
    else: return False

def isParallelFifth(vlq):
    rules = [vlq.parallelMotion() == True,
            vlq.vIntervals[1].simpleName == 'P5']
    if all(rules):
        return True
    else: return False

def isParallelOctave(vlq):
    rules = [vlq.parallelMotion() == True,
            vlq.vIntervals[1].name in ['P8', 'P15', 'P22']]
    if all(rules):
        return True
    else: return False

def isVoiceOverlap(vlq):
    rules = [vlq.v1n2.pitch < vlq.v2n1.pitch,
            vlq.v2n2.pitch > vlq.v1n1.pitch]
    if any(rules):
        return True
    else: return False

def isVoiceCrossing(vlq):
    rules = [vlq.v1n1.pitch > vlq.v2n1.pitch,
            vlq.v1n2.pitch < vlq.v2n2.pitch]
    if all(rules):
        return True
    else: return False

def isCrossRelation(vlq):
    rules = [interval.Interval(vlq.v1n1, vlq.v2n2).simpleName in ['d1', 'A1'],
            interval.Interval(vlq.v2n1, vlq.v1n2).simpleName in ['d1', 'A1']]
    if any(rules):
        return True
    else: return False
    
# Methods for notes

def isOnbeat(note):
    rules = [note.beat == 1.0]
    if any(rules):
        return True
    else: return False

def isSyncopated(score, note):
    # TODO this is a first attempt at defining the syncopation property
    #    given a time signature and music21's default metric system for it
    # this works for duple simple meter, not sure about compound or triple
    
    # get the time signature
    ts = score.recurse().getElementsByClass(meter.TimeSignature)[0]    

    # determine the length of the note
    # tied-over notes have no independent duration
    if note.tie == None:
        note.len = note.quarterLength
    elif note.tie.type == 'start':
        note.len = note.quarterLength + note.next().quarterLength
    elif note.tie.type == 'stop':
        note.len = 0
    # find the maximum metrically stable duration of a note initiated at t
    maxlen = note.beatStrength * note.beatDuration.quarterLength * ts.beatCount
    # determine whether the note is syncopated
    if n.len > maxlen: 
        return True
    elif n.len == 0:
        return None
    else:
        return False
    
def startWeight(score, note):
    # TODO this is a first attempt at defining metrical properties of notes
    # finds the metrical strength of a note's offsetStart

    # get the time signature
    ts = score.recurse().getElementsByClass(meter.TimeSignature)[0]    

    # determine the length of the note
    # tied-over notes have no independent duration
    if note.tie == None:
        note.len = note.quarterLength
    elif note.tie.type == 'start':
        note.len = note.quarterLength + note.next().quarterLength
    elif note.tie.type == 'stop':
        note.len = 0

    if note.len > 0:
        return note.beatStrength
    else:
        return None # or 0 ?

def stopWeight(score, note):
    # TODO this is a first attempt at defining metrical properties of notes
    # finds the metrical strength of a note's offsetEnd
    
    # get the time signature
    ts = score.recurse().getElementsByClass(meter.TimeSignature)[0]    

    # determine the length of the note
    # tied-over notes have no independent duration
    if note.tie == None:
        note.len = note.quarterLength
    elif note.tie.type == 'start':
        note.len = note.quarterLength + note.next().quarterLength
    elif note.tie.type == 'stop':
        note.len = 0

    if note.len > 0:
        pass
    else: 
        pass      


# -----------------------------------------------------------------------------

if __name__ == '__main__':
    # self_test code
#    pass
#    source='TestScoresXML/FirstSpecies01.musicxml'
#    source='TestScoresXML/FirstSpecies10.musicxml'
#    source='TestScoresXML/SecondSpecies20.musicxml'
#    source='TestScoresXML/SecondSpecies21.musicxml'
#    source='TestScoresXML/SecondSpecies22.musicxml'
    source='TestScoresXML/ThirdSpecies07.musicxml'
#    source='TestScoresXML/FourthSpecies01.musicxml'
#    source='TestScoresXML/FourthSpecies20.musicxml'
#    source='TestScoresXML/FourthSpecies21.musicxml'
#    source='TestScoresXML/FourthSpecies22.musicxml'
    
#    source = 'TestScoresXML/Test200.musicxml'
#    source = 'TestScoresXML/Test201.musicxml'

    cxt = context.makeGlobalContext(source)
    voiceLeadingAnalyzer(cxt)
    
# -----------------------------------------------------------------------------
# eof