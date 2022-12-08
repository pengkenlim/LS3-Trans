import os

programdir=os.path.join(os.getcwd(),"programs")
if __name__ == "__main__":
    print("Checking if required programs are installed...")


    #installing aspera if not installed
    installpath= os.path.join(programdir,"aspera")
    if not os.path.exists(installpath):
        print("Downloading and installing Aspera CLI into programs directory...")
        os.system("wget https://download.asperasoft.com/download/sw/cli/3.9.2/ibm-aspera-cli-3.9.2.1426.c59787a-linux-64-release.sh -O trashme.sh --no-check-certificate")
        os.system(f"sed -i \'s|~/.aspera|{installpath}|g\' trashme.sh")
        os.system("bash trashme.sh")
        os.system("rm trashme.sh")
    else:
        print("Aspera found.")


    #installing soapdenovotrans if not installed
    installpath = os.path.join(programdir, "SOAPdenovo-Trans-1.0.4")
    if not os.path.exists(installpath):
        print("Downloading and installing SOAPdenovo-Trans into programs directory.")
        os.system("wget https://github.com/aquaskyline/SOAPdenovo-Trans/archive/refs/tags/1.0.4.tar.gz -O trashme.tar.gz")
        os.system("tar -xf trashme.tar.gz")
        os.system("rm trashme.tar.gz")
        os.system(f"mv SOAPdenovo-Trans-1.0.4 {installpath}")
        os.system(f"cd {installpath} ; bash make.sh" )
    else:
        print("SOAPdenovo-Trans found.")


    #installing fastp if not installed
    installpath= os.path.join(programdir, "fastp")
    if not os.path.exists(installpath):
        print("Downloading and installing fastp into programs directory")
        os.system("wget http://opengene.org/fastp/fastp.0.23.2 -O fastp")
        os.system("chmod a+x fastp")
        os.system(f"mv fastp {installpath}")
    else:
        print("Fastp found.")


    #installing CD-HIT if not installed
    installpath= os.path.join(programdir, "CD-HIT")
    if not os.path.exists(installpath):
        print("Downloading and installing CD-HIT into programs directory")
        os.system("wget https://github.com/weizhongli/cdhit/releases/download/V4.8.1/cd-hit-v4.8.1-2019-0228.tar.gz -O trashme.tar.gz")
        os.system("tar -xf trashme.tar.gz")
        os.system("rm trashme.tar.gz")
        os.system(f"mv cd-hit-v4.8.1-2019-0228 {installpath}")
        os.system(f"cd {installpath} ; make")
    else:
        print("CD-HIT found.")

        
     
    installpath= os.path.join(programdir, "ORFfinder")
    if not os.path.exists(installpath):
        print("Downloading and installing ORFfinder into programs directory")
        os.system("wget https://ftp.ncbi.nlm.nih.gov/genomes/TOOLS/ORFfinder/linux-i64/ORFfinder.gz")
        os.system("gunzip ORFfinder.gz")
        os.system(f"mv ORFfinder {installpath}")
        #changing permissions for ORFfinder
        print("Changing permissions for ORFfinder. Password might be needed for sudo.")
        os.system(f"chmod 777 {installpath}")

    installpath= os.path.join(programdir, "kallisto")
    if not os.path.exists(installpath):
        print("Downloading and installing Kallisto into programs directory")
        os.system("wget https://github.com/pachterlab/kallisto/releases/download/v0.46.1/kallisto_linux-v0.46.1.tar.gz -O trashme.tar.gz")
        os.system("tar -xf trashme.tar.gz")
        os.system("rm trashme.tar.gz")
        os.system(f"mv kallisto {installpath}")
    else:
        print("Kallisto found.")

    
