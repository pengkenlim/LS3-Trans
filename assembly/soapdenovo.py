#setting sys.path for importing modules
import os
import sys
if __name__ == "__main__":
        abspath= os.getcwd()
        parent_module= os.path.join(abspath.split("LSTrAP-denovo")[0], "LSTrAP-denovo")
        sys.path.insert(0, parent_module)


import subprocess

from setup import constants

def make_config(fastqpath,configoutpath ):
    ''' make a config file with path to fastq.'''
    with open(configoutpath, "w") as f:
        f.write(f"max_rd_len=200\n[LIB]\nreverse_seq=0\nasm_flags=3\nq={fastqpath}")

def extract_orf(fastainputpath, fastaoutputpath, orfminlen, startcodon, geneticcode):
    returncode= subprocess.run([constants.orffinderpath, "-in", fastainputpath, "-out", fastaoutputpath, "-ml", str(orfminlen), "-s", str(startcodon), "-g", str(geneticcode), "-outfmt", "1"],
    stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    return returncode.returncode
    
    
def launch_soap(configoutpath, kmerlen, outputpath_prefix, threads):
    returncode=subprocess.run([constants.soappath, "all", "-s", configoutpath, "-o", outputpath_prefix+"_temp", "-K", str(kmerlen), "-p", str(threads), "-t", "20"],
    stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    return returncode.returncode
    
def launch_soap_verbose(configoutpath, kmerlen, outputpath_prefix, threads):
    returncode=subprocess.run([constants.soappath, "all", "-s", configoutpath, "-o", outputpath_prefix+"_temp", "-K", str(kmerlen), "-p", str(threads), "-t", "20"])
    return returncode.returncode

