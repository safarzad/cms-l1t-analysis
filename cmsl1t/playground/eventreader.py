from __future__ import print_function
from rootpy.tree import TreeChain
import six
# import inspect
import math

from jetfilters import defaultJetFilter
from cmsl1t.playground.cache import CachedIndexedTree
import ROOT
from collections import namedtuple

if 'L1TAnalysisDataformats.so' not in ROOT.gSystem.GetLibraries():
    ROOT.gSystem.Load('build/L1TAnalysisDataformats.so')
sumTypes = ROOT.l1t.EtSum

# some quick classes

Sum = namedtuple('Sum', ['et'])
Met = namedtuple('Met', ['et', 'phi'])
Mex = namedtuple('Mex', ['ex'])
Mey = namedtuple('Mey', ['ey'])

TREE_NAMES = [
    'l1CaloTowerTree/L1CaloTowerTree',
    'l1CaloTowerEmuTree/L1CaloTowerTree',
    'l1JetRecoTree/JetRecoTree',
    'l1MetFilterRecoTree/MetFilterRecoTree',
    'l1MuonRecoTree/Muon2RecoTree',
    'l1RecoTree/RecoTree',
    'l1UpgradeTree/L1UpgradeTree',
    'l1UpgradeEmuTree/L1UpgradeTree',
]


class Event(object):

    energySumTypes = {
        sumTypes.kTotalEt: {'name': 'Ett', 'type': Sum},
        sumTypes.kTotalEtHF: {'name': 'EttHF', 'type': Sum},
        sumTypes.kTotalHt: {'name': 'Htt', 'type': Sum},
        sumTypes.kTotalHtHF: {'name': 'HttHF', 'type': Met},
        sumTypes.kMissingEt: {'name': 'Met', 'type': Met},
        sumTypes.kMissingEtHF: {'name': 'MetHF', 'type': Met},
        sumTypes.kMissingHt: {'name': 'Mht', 'type': Met},
        sumTypes.kTotalEtx: {'name': 'Mex', 'type': Mex},
        sumTypes.kTotalEty: {'name': 'Mey', 'type': Mey},
    }

    def __init__(self, trees):
        self._trees = trees
        # add names, aliases?
        # lets assume fixed for now:
        self._caloTowers, self._emuCaloTower, self._jetReco,\
            self._metFilterReco, self._muonReco, self._recoTree,\
            self._upgrade, self._emuUpgrade = self._trees

        self._caloTowers = CachedIndexedTree(
            self._caloTowers.L1CaloTower, 'nTower')
        self._emuCaloTower = CachedIndexedTree(
            self._emuCaloTower.L1CaloTower, 'nTower')
        self._upgrade = self._upgrade.L1Upgrade
        self._emuUpgrade = self._emuUpgrade.L1Upgrade

        self._jets = []
        for i in range(self._jetReco.Jet.nJets):
            self._jets.append(Jet(self._jetReco.Jet, i))

        self._l1Sums = {}
        self._readUpgradeSums()
        self._readEmuUpgradeSums()

    def _readUpgradeSums(self):
        self._readSums(self._upgrade, prefix='L1')

    def _readEmuUpgradeSums(self):
        self._readSums(self._emuUpgrade, prefix='L1Emu')

    def _readSums(self, tree, prefix='L1'):
        sums = {}
        for i in range(tree.nSums):
            bx = tree.sumBx[i]
            if bx != 0:
                continue

            sumType = tree.sumType[i]
            et = tree.sumEt[i]
            phi = tree.sumPhi[i]
            if sumType in Event.energySumTypes:
                name = Event.energySumTypes[sumType]['name']
                obj = Event.energySumTypes[sumType]['type']
                if obj == Met:
                    sums[prefix + name] = obj(et, phi)
                else:
                    sums[prefix + name] = obj(et)
        self._l1Sums.update(sums)

    def test(self):
        # for tree in self._trees:
        #     print(tree)
        print('>>>> nHCALTP', self._caloTowers.CaloTP.nHCALTP)
        print('>>>> nHCALTP (emu)', self._emuCaloTower.CaloTP.nHCALTP)
        print('>>>> nJets', self._jetReco.Jet.nJets)
        print('>>>> met', self._jetReco.Sums.met)
        print('>>>> hbheNoiseFilter',
              self._metFilterReco.MetFilters.hbheNoiseFilter)
        print('>>>> nMuons', self._muonReco.Muon.nMuons)
        print('>>>> nVtx', self._recoTree.Vertex.nVtx)
        print('>>>> nJets (upgrade)', self._upgrade.nJets)
        print('>>>> nJets (upgrade emu)', self._emuUpgrade.nJets)
        print('>>>> nSums (upgrade)', self._upgrade.nSums)
        print('>>>> nSums (upgrade emu)', self._emuUpgrade.nSums)
        print('>>>> L1 energy sums:')
        for name, value in six.iteritems(self.l1Sums):
            print('>>>>>>>> {0} = {1}'.format(name, value))
        print(self._jets[0].eta)
        leadingJet = self.getLeadingRecoJet()
        if leadingJet:
            print('>>>> Leading reco jet ET', leadingJet.etCorr)
        goodJets = self.goodJets()
        if goodJets:
            print('>>>> Lowest good jet ET', goodJets[-1].etCorr)

        # print(dir(self._jetReco.Jet))
        # members = inspect.getmembers(self._jetReco.Jet)
        # print('>>>> Jet members')
        # for m in members:
        #     print('>' * 6, m[0], ':', m[1])

    def goodJets(self, jetFilter=defaultJetFilter):
        '''
            filters and ET orders the jet collection
        '''
        goodJets = filter(jetFilter, self._jets)
        sorted_jets = sorted(
            goodJets, key=lambda jet: jet.etCorr, reverse=True)
        return sorted_jets

    def getLeadingRecoJet(self, jetFilter=defaultJetFilter):
        goodJets = self.goodJets(jetFilter)
        if not goodJets:
            return None
        leadingRecoJet = goodJets[0]
        if leadingRecoJet.etCorr > 10.0:
            return leadingRecoJet
        return None

    def getMatchedL1Jet(self, recoJet, l1Type='HW'):
        l1Jets = None
        if l1Type == 'HW':
            l1Jets = [L1Jet(self._upgrade, i)
                      for i in range(self._upgrade.nJets)]
        if l1Type == 'EMU':
            l1Jets = [L1Jet(self._emuUpgrade, i)
                      for i in range(self._emuUpgrade.nJets)]

        if not l1Jets or not recoJet:
            return None
        minDeltaR = 0.3
        closestJet = None
        for l1Jet in l1Jets:
            dEta = recoJet.eta - l1Jet.eta
            dPhi = recoJet.phi - l1Jet.phi
            dR = math.sqrt(dEta**2 + dPhi**2)
            if dR < minDeltaR:
                minDeltaR = dR
                closestJet = l1Jet
        return closestJet

    @property
    def nVertex(self):
        return self._recoTree.Vertex.nVtx

    @property
    def caloTowers(self):
        return self._caloTowers

    @property
    def emuCaloTowers(self):
        return self._emuCaloTower

    @property
    def sums(self):
        return self._jetReco.Sums

    def passesMETFilter(self):
        return self._metFilterReco.MetFilters.hbheNoiseFilter

    @property
    def l1Sums(self):
        return self._l1Sums


class Jet(object):
    '''
        Create a simple python wrapper for
        L1Analysis::L1AnalysisRecoJetDataFormat
    '''

    def __init__(self, jets, index):
        # this could be simplified with a list of attributes
        read_attributes = [
            'etCorr', 'muMult', 'eta', 'phi', 'nhef', 'pef', 'mef', 'chMult',
            'elMult', 'nhMult', 'phMult', 'chef', 'eef'
        ]
        for attr in read_attributes:
            setattr(self, attr, getattr(jets, attr)[index])

    @property
    def sumMult(self):
        return self.chMult + self.chMult + self.elMult
        # not
        # return self.chMult + self.muMult + self.elMult ?

    @property
    def allMult(self):
        return self.sumMult + self.nhMult + self.phMult


class L1Jet(object):

    def __init__(self, l1Jets, index):
        self.et = l1Jets.jetEt[index]
        self.eta = l1Jets.jetEta[index]
        self.phi = l1Jets.jetPhi[index]


class EventReader(object):
    '''
        There are many ways to tune the reader:
        http://rootpy-log.readthedocs.io/en/latest/_modules/rootpy/tree/chain.html
    '''

    def __init__(self, files, events=-1):
        # this is not efficient
        self._trees = [TreeChain(name, files, cache=True, events=events)
                       for name in TREE_NAMES]

    def __iter__(self):
        for trees in six.moves.zip(*self._trees):
            yield Event(trees)


if __name__ == '__main__':
    import glob
    # import ROOT
    # ROOT.gSystem.Load('build/L1TAnalysisDataformats.so')
    files = glob.glob('data/*.root')

    reader = EventReader(files)
    i = 1
    for event in reader:
        print('-' * 80)
        print('>> event', i)
        event.test()
        print('-' * 80)
        i += 1
        if i > 3:
            break
