__author__ = 'Nabeel'
import time, sys


def main(args):

    path = args[1];

    file1 = open(path, 'r')

    NFV1 = file1.read()

    NFV1_old = NFV1

    T = 30.0    # target load
    X_t = 0.0   # load to send to VNF2
    X_t_1 = 0.0 # load to send to VNF2 at t+1
    K = 0.2     # how fast to change
    L1 = 0.0    # load on VNF1

    while(True):

        time.sleep(1.5)

        # that means files have changed
        if NFV1_old != NFV1:
            try:
                NFV1_latest = float(NFV1.split("=")[-1])

                NFV1_old = (NFV1_old.split("=")[-1])
            except:
                print "Error is converting values!!!"
                NFV1_old = NFV1
                file1 = open(path, 'r')
                NFV1 = file1.read()
                continue;
            
            L1 = NFV1_latest

            X_t_1 = max(0, min(1, X_t + K * (L1-T)/T ))

			# get the last value for CPU usage
            print "Target CPU load at VNF1:            ", T
            print "Current CPU load at VNF1:           ", NFV1.split("=")[-1]
            print "% of flows to be send to VNF2:      ", X_t_1*100,'%'
            print "% of flows previously send to VNF2: ", X_t*100, '%'
            print ""

            # updates things
            NFV1_old = NFV1
            
            X_t = X_t_1
            f_out = open("NFV_ratio_PI.txt",'w')
            f_out.write("X="+str(X_t))

        file1 = open(path, 'r')
        
        NFV1 = file1.read()

if __name__ == "__main__":
   main(sys.argv)
