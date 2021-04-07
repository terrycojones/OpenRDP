from do_scans import *
from itertools import combinations
import configparser


class Scanner:
    def __init__(self, aln, args):
        self.infile = args.infile
        self.aln = aln
        self.rdp = True if args.rdp else False
        self.geneconv = True if args.geneconv else False
        self.threeseq = True if args.threeseq else False
        self.maxchi = True if args.maxchi else False
        self.chimaera = True if args.chimaera else False
        self.siscan = True if args.siscan else False
        self.bootscan = True if args.bootscan else False

        if args.cfg:
            self.cfg_file = args.cfg
        else:
            self.cfg_file = None

    def run_scans(self):
        """
        Run the selected recombination detection analyses
        """
        # Parse config file
        if self.cfg_file:
            config = configparser.ConfigParser()
            config.read(self.cfg_file)
        else:
            config = None

        seq_num = []
        aln_seqs = []
        for i, pair in enumerate(self.aln):
            seq_num.append(i)
            aln_seqs.append(pair[1])

        # Create an m x n array of sequences (n = length, m = number of sequences)
        alignment = np.array(list(map(list, aln_seqs)))

        # Run 3Seq
        if self.threeseq:
            three_seq = ThreeSeq(self.infile)
            print("Staring 3Seq Analysis")
            ts_results = three_seq.execute()
            print("Finished 3Seq Analysis")
            print(ts_results)

        # Run GENECONV
        if self.geneconv:
            if config:
                geneconv = GeneConv(settings=config['Geneconv'])
            else:
                geneconv = GeneConv()
            print("Starting GENECONV Analysis")
            gc_results = geneconv.execute(self.infile)

            print("Finished GENECONV Analysis")
            print(gc_results)

        # Exit early if 3Seq and Geneconv are the only methods selected
        if not self.maxchi and not self.chimaera and not self.siscan and not self.rdp and not self.bootscan:
            return

        # Setup MaxChi
        if self.maxchi:
            print("Starting MaxChi Analysis")
            if config:
                maxchi = MaxChi(alignment, settings=config['MaxChi'])
            else:
                maxchi = MaxChi(alignment)

        # Setup Chimaera
        if self.chimaera:
            print("Starting Chimaera Analysis")
            if config:
                chimaera = Chimaera(alignment, settings=config['Chimaera'])
            else:
                chimaera = Chimaera(alignment)

        # Setup Siscan
        if self.siscan:
            print("Starting Siscan Analysis")
            if config:
                siscan = Siscan(alignment, settings=config['SisScan'])
            else:
                siscan = Siscan(alignment)

        # Setup RDP
        if self.rdp:
            print("Starting RDP Analysis")
            if config:
                rdp = RdpMethod(alignment, settings=config['RDP'])
            else:
                rdp = RdpMethod(alignment)

        # Setup Bootscan
        if self.bootscan:
            if config:
                bootscan = Bootscan(alignment, settings=config['Bootscan'])
            else:
                bootscan = Bootscan(alignment)

        i = 1
        num_trp = len(list(combinations(seq_num, 3)))
        for triplet in list(combinations(seq_num, 3)):
            print("Scanning triplet {} / {}".format(i, num_trp))
            # Run MaxChi
            if self.maxchi:
                maxchi.execute(triplet)

            # Run Chimaera
            if self.chimaera:
                chimaera.execute(triplet)

            # Run Siscan
            if self.siscan:
                siscan.execute(alignment, triplet)

            # Run RDP Method
            if self.rdp:
                rdp.execute(alignment, triplet, num_trp)

            # Run Bootscan
            if self.bootscan:
                print("Starting Bootscan Analysis")
                bs_results = bootscan.execute(alignment, triplet, num_trp)
                print("Finished Bootscan Analysis")
                print(bs_results)

            i += 1

        # Report the results
        if self.maxchi:
            print("Finished MaxChi Analysis")
            print(maxchi.results)

        if self.chimaera:
            print("Finished Chimaera Analysis")
            print(chimaera.results)

        if self.siscan:
            print("Finished Siscan Analysis")
            print(siscan.results)

        if self.rdp:
            print("Finished RDP Analysis")
            print(rdp.results)
