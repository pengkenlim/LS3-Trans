import os
import sys
abspath=os.getcwd()
programdir= os.path.join(abspath.split("LSTrAP-denovo")[0], "LSTrAP-denovo","programs")

fastppath= os.path.join(programdir,"fastp")
asperapath=os.path.join(programdir,"aspera","cli", "bin", "ascp")
aspera_ssh_key= os.path.join(programdir,"aspera","cli","etc","asperaweb_id_dsa.openssh")
soappath= os.path.join(programdir,"SOAPdenovo-Trans-1.0.4", "SOAPdenovo-Trans-127mer" )
orffinderpath= os.path.join(programdir,"ORFfinder")
cdhitpath= os.path.join(programdir,"CD-HIT", "cd-hit-est")
kallistopath= os.path.join(programdir, "kallisto", "kallisto")
__all__=["asperapath", "aspera_ssh_key", "fastppath", "soappath", "orffinderpath", "kallistopath"]
