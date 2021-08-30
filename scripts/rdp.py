import re

import numpy as np


class RdpMethod:
    """
    Executes RDP method
    """
    def __init__(self, align, win_size=30, reference=None, min_id=0, max_id=100, settings=None):
        if settings:
            self.set_options_from_config(settings)
            self.validate_options()

        else:
            self.win_size = win_size
            self.reference = reference
            self.min_id = min_id
            self.max_id = max_id

        self.align = align
        self.results = {}

    def set_options_from_config(self, settings):
        """
        Set the parameters of the RDP method from the config file
        :param settings: a dictionary of settings
        """
        self.win_size = int(settings['window_size'])
        self.reference = settings['reference_sequence']
        self.min_id = int(settings['min_identity'])
        self.max_id = int(settings['max_identity'])

    def validate_options(self):
        """
        Check if the options from the config file are valid
        If the options are invalid, the default value will be used instead
        """
        if self.reference == 'None':
            self.reference = None

        if self.win_size < 0:
            print("Invalid option for 'window_size'.\nUsing default value (30) instead.")
            self.win_size = 30

        if self.min_id < 0 or self.min_id > 100:
            print("Invalid option for 'min_identity'.\nUsing default value (0) instead.")
            self.min_id = 0

        if self.max_id < 0 or self.max_id > 100:
            print("Invalid option for 'max_identity'.\nUsing default value (100) instead.")
            self.min_id = 100

    def triplet_identity(self, triplets):
        """
        Calculate the percent identity of each triplet and
        :param triplets: a list of all triplets
        :return: triplets whose identity is greater than the minimum identity and less than the maximum identity
        """
        trps = []
        for trp in triplets:
            ab = np.array([trp.sequences[0], trp.sequences[1]])
            bc = np.array([trp.sequences[1], trp.sequences[2]])
            ac = np.array([trp.sequences[0], trp.sequences[2]])
            ab, bc, ac = self.pairwise_identity(ab, bc, ac)

            # Include only triplets whose identity is valid
            if self.min_id < ab < self.max_id and self.min_id < bc < self.max_id and self.min_id < ac < self.max_id:
                trps.append(trp)

        return trps

    @staticmethod
    def pairwise_identity(reg_ab, reg_bc, reg_ac):
        """
        Calculate the pairwise identity of each sequence within the triplet
        :param reg_ab: matrix of size 2 x sequence_length that contains sequences A and B
        :param reg_bc: matrix of size 2 x sequence_length that contains sequences B and C
        :param reg_ac: matrix of size 2 x sequence_length that contains sequences A and C
        :return: the identity of each pair of sequences in the triplet
        """
        a_b, b_c, a_c = 0, 0, 0

        for j in range(reg_ab.shape[1]):
            if reg_ab[0, j] == reg_ab[1, j]:
                a_b += 1
            if reg_bc[0, j] == reg_bc[1, j]:
                b_c += 1
            if reg_ac[0, j] == reg_ac[1, j]:
                a_c += 1

        percent_identity_ab = a_b / reg_ab.shape[1] * 100
        percent_identity_bc = b_c / reg_bc.shape[1] * 100
        percent_identity_ac = a_c / reg_ac.shape[1] * 100

        return percent_identity_ab, percent_identity_bc, percent_identity_ac

    def execute(self, triplets, quiet=False):
        """
        Performs RDP detection method for one triplet of sequences
        :return: the coordinates of the potential recombinant region and the p_value
        """

        # Get the triplet sequences
        trps = self.triplet_identity(triplets)

        trp_count = 1
        G = len(trps)
        for triplet in trps:
            if not quiet:
                print("Scanning triplet {} / {}".format(trp_count, G))
            trp_count += 1

            names = tuple(triplet.names)
            self.results[names] = []

            # Get the three pairs of sequences
            ab = np.array([triplet.info_sites_align[0], triplet.info_sites_align[1]])
            bc = np.array([triplet.info_sites_align[1], triplet.info_sites_align[2]])
            ac = np.array([triplet.info_sites_align[0], triplet.info_sites_align[2]])

            len_trp = triplet.info_sites_align.shape[1]

            # 2. Sliding window over subsequence and calculate average percent identity at each position
            recombinant_regions = ''  # Recombinant regions denoted by ones
            coord = []
            for i in range(len_trp - self.win_size):
                reg_ab = ab[:, i: self.win_size + i]
                reg_bc = bc[:, i: self.win_size + i]
                reg_ac = ac[:, i: self.win_size + i]

                # Calculate percent identity in each window
                percent_identity_ab, percent_identity_bc, percent_identity_ac = self.pairwise_identity(reg_ab, reg_bc, reg_ac)

                # Identify recombinant regions
                if percent_identity_ac > percent_identity_ab or percent_identity_bc > percent_identity_ab:
                    recombinant_regions += "1"
                    coord.append(i)
                else:
                    recombinant_regions += "0"

            # 3. Record significance of events
            recomb_idx = [(m.span()) for m in re.finditer('1+', recombinant_regions)]

            # Convert coordinates from  window-level to alignment-level and record number of windows
            coords = []
            for x, y in recomb_idx:
                coords.append((triplet.info_sites[x], triplet.info_sites[y - 1]))

            for coord in coords:
                n = coord[1] - coord[0]     # Length of putative recombinant region

                if n > 0:
                    # m is the proportion of nts in common between either A or B and C in the recombinant region
                    nts_in_a = triplet.sequences[0][coord[0]: coord[1]]
                    nts_in_c = triplet.sequences[2][coord[0]: coord[1]]
                    m = 0
                    for i in range(n):
                        if nts_in_a[i] == nts_in_c[i]:
                            m += 1

                    # p is the proportion of nts in common between either A or B and C in the entire subsequence
                    id_in_seq = 0
                    for j in range(triplet.sequences.shape[1]):
                        if triplet.sequences[0][j] == triplet.sequences[2][j]:
                            id_in_seq += 1
                    p = id_in_seq / triplet.sequences.shape[1]

                    # Calculate p_value
                    val = 0
                    log_n_fact = np.sum(np.log(np.arange(1, n+1)))  # Convert to log space to prevent integer overflow
                    for i in range(m, n):
                        log_i_fact = np.sum(np.log(np.arange(1, i+1)))
                        log_ni_fact = np.sum(np.log(np.arange(1, n-i+1)))
                        try:
                            val += np.math.exp((log_n_fact - (log_i_fact + log_ni_fact)) + np.log(p**n) + np.log((1-p)**(n-i)))
                        except ZeroDivisionError:
                            pass

                    uncorr_pvalue = (len_trp / n) * val
                    corr_p_value = G * uncorr_pvalue

                else:
                    uncorr_pvalue = 'NS'
                    corr_p_value = 'NS'

                if uncorr_pvalue != 'NS' or corr_p_value != 'NS':
                    try:
                        self.results[names].append((coord, uncorr_pvalue, corr_p_value))
                    except KeyError:
                        self.results[names] = (coord, uncorr_pvalue, corr_p_value)

        return self.results
