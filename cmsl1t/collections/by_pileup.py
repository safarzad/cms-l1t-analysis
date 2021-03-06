from collections import defaultdict
from rootpy.plotting import Hist

from cmsl1t.utils.iterators import pairwise
from cmsl1t.io import to_root
from . import BaseHistCollection


# TODO: inherit from BinnedHistogramCollection

class HistogramsByPileUpCollection(BaseHistCollection):
    '''
        Specialisation of BaseHistCollection to bin histograms by pileup

        :Example:
            >>> hists = HistogramsByPileUp(pileupBins=[0,10,15,20,30,999])
            >>> pileup=11
            >>> # translates pileup=11 to 2nd pileup bin
            >>> hists[pileup] = Hist(bins=np.arange(-1, 1.5, 0.05))
    '''

    def __init__(self, pileupBins, dimensions=1, initiaValue=0):
        BaseHistCollection.__init__(self, dimensions, initiaValue)
        self._pileupBins = pileupBins
        self._pileupHist = Hist(100, 0, 100, name='nVertex')

    def set_pileup(self, pileUp):
        self._pileUp = pileUp
        self._pileupHist.fill(pileUp)

    def _get_pu_bin(self, pileup):
        '''
            Returns the pileup bin corresponding to the provided pileup value.

            :Example:
                >>> hists = HistogramsByPileUp(pileupBins=[0,10,15,20,30,999])
                >>> hists._get_pu_bin(1) # returns 0
                >>> hists._get_pu_bin(11) # returns 1
                >>> hists._get_pu_bin(1111) # returns -1
        '''
        if pileup > max(self._pileupBins):
            return -1

        bins = pairwise(self._pileupBins)
        for i, (lowerEdge, upperEdge) in enumerate(bins):
            if pileup >= lowerEdge and pileup < upperEdge:
                return i
        return 0

    def __getitem__(self, key):
        real_key = self._get_pu_bin(key)
        return defaultdict.__getitem__(self, real_key)

    def summarise(self):
        '''
            Sums histograms across PU bins
        '''
        raise NotImplementedError

    def to_root(self, output_file):
        '''
            Saves the instance into a ROOT file
        '''
        # need to add pileupHist manually
        to_root([self, self._pileupHist], output_file)

    @staticmethod
    def from_root(input_file):
        from rootpy.io.pickler import load
        instance, pileupHist = load(input_file)
        instance._pileupHist = pileupHist
        return instance
