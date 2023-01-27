#setting sys.path for importing modules
import os
import sys
if __name__ == "__main__":
        abspath= os.getcwd()
        parent_module= os.path.join(abspath.split("LSTrAP-denovo")[0], "LSTrAP-denovo")
        sys.path.insert(0, parent_module)

import argparse
import concurrent.futures
import random
import numpy as np
from time import sleep
from datetime import datetime

from tqdm import tqdm
from download import ena
from download import aspera
from assembly import soapdenovo, misc , postprocess, report
from setup import constants
from preprocess import trim




def single_sample_assembly(accession,index):
    '''Job to generate Single-sample assembly. 
    Validate download path -> download via ftp/ascp-> read trimming by fastp -> assembly by soapdenovo-Trans'''
    logfile.load()
    if accession in logfile.contents["Step_1"]["processed_acc"].keys():
        print(f"{accession} already processed. Skipping accession...")
        return f"{accession} already processed."
    #to un-sync workers 
    sleep((index%workers)*10)
    ascp_fullpath,ftp_fullpath,filesize = logfile.contents["Step_1"]["run_var"]["selected_accessions"].get(accession)
    #check if paired or if forward > filesizelimit
    if len(ascp_fullpath) == 1 or filesize[0] >= filesizelimit:
        fastqpath=os.path.join(fastqdir,accession+".fastq.gz")
    #use the appropriate download method to download accession
        if download_method == "ascp" :
            result= misc.run_with_retries(retrylimit,
            aspera.launch_ascp,
            [ascp_fullpath[0],fastqpath,filesizelimit],
            f"{accession}: Download failed. Retrying...",
            f"{accession}: Downloading file via ascp...\n")
            
        elif download_method == "ftp":
            result= misc.run_with_retries(retrylimit,
            aspera.launch_curl,
            [ftp_fullpath[0],fastqpath,filesizelimit],
            f"{accession}: Download failed. Retrying...",
            f"{accession}: Downloading file via ftp...\n")
        if result == "failed":
            logfile.load()
            logfile.contents["Step_1"]["processed_acc"][accession]= "Download failed."
            logfile.update()
            return f"{accession}: Aborted after {retrylimit} retries."
    else:
        fastqpath=os.path.join(fastqdir,accession+".fastq.gz")
        fastqpath_2=os.path.join(fastqdir,accession+"_2.fastq.gz")
        if download_method == "ascp":
            #download file 1, no download limit.
            result= misc.run_with_retries(retrylimit,
            aspera.launch_ascp,
            [ascp_fullpath[0],fastqpath,0],
            f"{accession}: Download failed. Retrying...",
            f"{accession}: Downloading file 1 via ascp...\n")
            if result == "failed":
                with open(pathtoprocessed, "a") as f:
                    f.write(f"{accession}\tDownload failed\n")
                return f"{accession}: Aborted after {retrylimit} retries."
            #download file 2, download limit = filesizelimit - filesize of file 1
            result= misc.run_with_retries(retrylimit,
            aspera.launch_ascp,
            [ascp_fullpath[1],fastqpath_2,filesizelimit - filesize[0] ],
            f"{accession}: Download failed. Retrying...",
            f"{accession}: Downloading file 2 via ascp...\n")
            
        elif download_method == "ftp":
            #download file 1, no download limit.
            result= misc.run_with_retries(retrylimit,
            aspera.launch_curl,
            [ftp_fullpath[0],fastqpath,0], 
            f"{accession}: Download failed. Retrying...",
            f"{accession}: Downloading file 1 via ftp...\n")
            if result == "failed":
                with open(pathtoprocessed, "a") as f:
                    f.write(f"{accession}\tDownload failed\n")
                return f"{accession}: Aborted after {retrylimit} retries."
            #download file 2, download limit = filesizelimit - filesize of file 1
            result= misc.run_with_retries(retrylimit,
            aspera.launch_curl,
            [ftp_fullpath[1],fastqpath_2,filesizelimit - filesize[0]],
            f"{accession}: Download failed. Retrying...",
            f"{accession}: Downloading file 2 via ftp...\n")
        if result == "failed":
            with open(pathtoprocessed, "a") as f:
                f.write(f"{accession}\tDownload failed\n")
            return f"{accession}: Aborted after {retrylimit} retries."
        #concatenate reverse reads to forward reads
        os.system(f"cat {fastqpath_2} >> {fastqpath}")
        os.system(f"rm {fastqpath_2}")
            
    #trim and uncompress
    result= misc.run_with_retries(retrylimit,
    trim.launch_fastp,
    [fastqpath, fastqpath.split(".gz")[0],threads],
    f"{accession}: Fastp trimming failed. Retrying...",
    f"{accession}: Trimming file using Fastp...\n")
    if result == "failed":
        with open(pathtoprocessed, "a") as f:
            f.write(f"{accession}\tFastP failed\n")
        return f"{accession}: Aborted after {retrylimit} retries."
    if os.path.getsize(fastqpath.split(".gz")[0]) < 100*1024*1024: # if too many reads were discarded by fastp (<100mb of reads left), then abort:
        with open(pathtoprocessed, "a") as f:
            f.write(f"{accession}\tFastP failed\n")
        return f"{accession}: Aborted. FastP error."
    #make config file for soapdenovotrans to parse
    fastqpath= fastqpath.split(".gz")[0]
    configoutpath = os.path.join(ssadir, accession + "_temp.config")
    soapdenovo.make_config(fastqpath,configoutpath)
    #Single-sample-assembly process
    outputpath_prefix= os.path.join(ssadir, accession)
    results=misc.run_with_retries(retrylimit,
    soapdenovo.launch_soap,
    [configoutpath, kmerlen, outputpath_prefix, threads],
    f"{accession}: Soapdenovo-Trans failed. Retrying...",
    f"{accession}: Assembling transcripts with Soapdenovo-Trans...\n")
    if result == "failed":
        with open(pathtoprocessed, "a") as f:
            f.write(f"{accession}\tAssembly failed\n")
        return f"{accession}: Aborted after {retrylimit} retries."
    
    #renaming transcript file to keep and deleting others
    os.system(f"mv {outputpath_prefix}_temp.scafSeq {outputpath_prefix}.fasta")
    os.system(f"rm -r {outputpath_prefix}_temp*")

    #remove uncompressed and trimmed fastq file to save space
    os.system(f"rm {fastqpath}")
        
    #extract orf from assembly to get cds.fasta
    results= misc.run_with_retries(retrylimit,
    soapdenovo.extract_orf,
    [outputpath_prefix + ".fasta", outputpath_prefix + "_cds.fasta", orfminlen, startcodon , geneticcode],
    f"{accession}: ORFfinder failed. Retrying...",
    f"{accession}: Extracting CDS with ORFfinder...\n")
    if result == "failed":
        with open(pathtoprocessed, "a") as f:
            f.write(f"{accession}\tAssembly failed\n")
        return f"{accession}: Aborted after {retrylimit} retries."
    os.system(f"rm {outputpath_prefix}.fasta")
    n_cds, _, _ = misc.get_assembly_stats(outputpath_prefix + "_cds.fasta")
    with open(pathtoprocessed, "a") as f:
        f.write(f"{accession}\t{n_cds}\n")
    print(f"{accession}: Single-sample assembly completed.")
    return f"{accession} processed"    
    
def parallel_ssa(workers):
    ''' Wrapper to parallelize SSA jobs. 
    Includes progress bar visualisation.'''
    logfile.load()
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
                progress_bar= tqdm(total=len(logfile.contents["Step_1"]["run_var"]["selected_accessions"]), desc= "Accessions processed", unit="Acsn", leave=True)
                results= [executor.submit(single_sample_assembly, accession, index) for index, accession in enumerate(logfile.contents["Step_1"]["run_var"]["selected_accessions"])]
                for f in concurrent.futures.as_completed(results):
                    if "processed" in f.result():
                        progress_bar.update(1)
                        #print("\n")
                        progress_bar.set_postfix_str(s=f.result())
                        print("\n")
                    else:
                        print(f.result())
                progress_bar.close()
                logfile.load()
                


                    
                    
                

def ssa_consensus(assemblydir):
    """ generate consensus assembly from SSAs"""
    logfile.load()
    print("\nConcatenating all Single-sample assemblies...\n")
    #make subdir within assemblydir to store consensus assemblies
    outputdir=os.path.join(assemblydir, "concat")
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)
    #concatenate and rename transcript ids
    concatname="ssa_concat_cds.fasta"
    concatpath=os.path.join(outputdir,concatname)
    postprocess.concat_rename_assemblies(assemblydir,concatpath)
    #launch CD-HIT in shell with retry wrapper
    clstr_concatpath= os.path.join(outputdir,"ssa_concat_cds_CT1.fasta")
    result=misc.run_with_retries(retrylimit, 
    postprocess.launch_cdhit, 
    [concatpath,0.998,clstr_concatpath, threadpool],
    "CD-HIT-EST failed. Retrying...\n", 
    "Running CD-HIT-EST on concatenated assembly...\n")
    if result == "failed":
        sys.exit(f"CD-HIT-EST aborted after aborted after {retrylimit} retries. Exiting...")
    clstrinfopath = clstr_concatpath + ".clstr" 
    print("Parsing output from CD-HIT-EST and extracting sequences...\n")
    #extract sequence IDs to retain for each consensus threshold
    logfile.contents["Step_1"]["consensus"]["stats"]={}
    logfile.update()
    #temporary list to hold n_CDS
    temp_list=[]
    for n_threshold in range(1,len([cds for cds in os.listdir(assemblydir) if "cds.fasta" in cds])+1):
        seq_to_retain= postprocess.cluster_seq_extractor(n_threshold,clstrinfopath)
        consensus_ssa_path= os.path.join(outputdir,f"ssa_concat_cds_CT{n_threshold}.fasta")
        postprocess.fasta_subset(clstr_concatpath, consensus_ssa_path, seq_to_retain)
        print(f"Preliminary assembly generated at {consensus_ssa_path} using consensus threshold of {n_threshold}.")
        n_cds, avg_cds_len, GC = misc.get_assembly_stats(consensus_ssa_path)
        print(f"No. of CDS: {n_cds}\nAvg. CDS len: {avg_cds_len}\nGC content: {GC}%\n")
        logfile.contents["Step_1"]["consensus"]["stats"][n_threshold]= [n_cds, avg_cds_len ,GC, consensus_ssa_path]
        temp_list+=[n_cds]
    logfile.update()
    target_cds= np.median([k for k in logfile.contents["Step_1"]["processed_acc"].values() if type(k) is int])
    logfile.contents["Step_1"]["consensus"]["optimal"]= int(postprocess.CT_from_target_CDS(temp_list,target_cds))
    logfile.update()
    print("Consensus threshold of " + str(logfile.contents["Step_1"]["consensus"]["optimal"])+" has been determined to be optimal.\n")


     
    
        
        
        
    


if __name__ == "__main__":
	#retry limit determines the number of retries before aborting
    retrylimit=2
    
    #arguments
    parser= argparse.ArgumentParser(description="LSTrAP-denovo.MakeDraftCDS.py: Assemble draft coding sequences from public RNA-seq data.\n\
     Refer to https://github.com/pengkenlim/LSTrAP-denovo for more information on pipeline usage and implementation.")
    parser.add_argument("-o", "--output_dir", type=str, metavar= "", required=True,
    help= "Directory for data output.")
    parser.add_argument("-k", "--kmer_len", type=int, metavar="", default=35, choices=range(21, 49+1,2), 
    help = "Specifies K-mer length (odd integer only) for assembly using Soapdenovo-Trans. K-mer length will be set to 35 by default.")
    parser.add_argument("-s","--filesizelimit" , type=int, metavar="", default=1500, 
    help="Specifies the parital download limit/ file size requirement(mb) of accession read files. Limit set to 1500 (mb) by default.")
    parser.add_argument("-t", "--threads", type=int, metavar="", default=4, 
    help = "Total thread pool for workers. Needs to be divisible by number of workers.")
    parser.add_argument("-w", "--workers", type=int, metavar="", default=2, 
    help= "Specifies the maximum workers for running multiple download-assembly jobs in parallel. Set to 2 by default.")
    parser.add_argument("-g", "--gene_code", type=int, metavar="", default=1, choices=range(1, 31), 
    help= "Genetic code (codon table) passed to ORFfinder during ORF extraction. Set to 1 (universal) by default. Refer to https://www.ncbi.nlm.nih.gov/Taxonomy/Utils/wprintgc.cgi for more information.")
    parser.add_argument("-sc", "--start_codon", type=int, metavar="", default=0, choices=range(0, 2+1),
    help= "ORF start codon passed to ORFfinder during ORF extraction. Set to 0 (ATG only) by default. Refer to ORFfinder usage https://ftp.ncbi.nlm.nih.gov/genomes/TOOLS/ORFfinder/USAGE.txt for more information")
    parser.add_argument("-ml", "--min_len", type=int, metavar="", default=300, choices=range(30, 500),
    help= "Minimal ORF length (nt) passed to ORFfinder during ORF extraction. Set to 300 by default.")
    parser.add_argument("-dm", "--download_method", type=str, metavar="", default="ascp", choices=["ascp","ftp"],
    help = "Method to download accession runs. ftp/ascp. Set to aspera download (ascp) by default.")
    parser.add_argument("-na", "--n_accessions", type=int, metavar="", default=10, choices=range(10,50+1), 
    help = "Number of single-accession-assemblies to combine in order to generate the preliminary assembly.")
    parser.add_argument("-a", "--accessions", type=str, metavar="",
    help= "User-defined list of ENA run accessions to fetch for preliminary assembly. If insufficient accessions provided, run will be supplemented with other public accessions. E.g.: SRR123456,SRR654321,ERR246810,...")
    #mutually exclusive argumentss for initial run or resume incomplete run
    ME_group_1 = parser.add_mutually_exclusive_group(required=True)
    ME_group_1.add_argument("-i", "--id", type=int, metavar="", 
    help= "NCBI TaxID of organism for fetching ENA run accessions.")
    ME_group_1.add_argument("-con", "--conti", action="store_true",
    help = "Resume incomplete run based on output directory. Only requires -o to run.")
    
    #banner
    misc.print_logo("MakeDraftCDS.py")
    
    args=parser.parse_args()
    outputdir= args.output_dir
    conti=args.conti
    #create outputdir , fastqdir and ssadir if not found
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)    
    fastqdir=os.path.join(outputdir,"Step_1","fastq")
    ssadir=os.path.join(outputdir, "Step_1","ssa")
    if not os.path.exists(fastqdir):
        os.makedirs(fastqdir)
    if not os.path.exists(ssadir):
        os.makedirs(ssadir)
    logfile=misc.logfile(os.path.join(outputdir,"logs.json"))
    
    #assigning arguments to variables, writing to log OR fetching variables from log
    if conti==False:
        taxid= args.id
        selected_accessions= args.accessions
        ##consensus_threshold= args.consensus_threshold
        filesizelimit= args.filesizelimit * 1048576
        threadpool= args.threads
        workers=args.workers
        kmerlen=args.kmer_len
        orfminlen=args.min_len
        startcodon=args.start_codon
        geneticcode=args.gene_code
        download_method= args.download_method
        n_accessions = args.n_accessions
        
        #getting sciname and accessions from ena using taxid
        scientific_name= ena.get_sciname(taxid)
        if type(scientific_name) is  not list:
            sys.exit(f"TaxID {taxid} is invalid/not found. Exiting...")
        elif len(scientific_name) > 1:
            sys.exit(f"More than one organism found for TaxID {taxid}. Exiting...")
        scientific_name= scientific_name[0]["scientific_name"]
        print(f"\nFetching RNA-seq accessions of {scientific_name} (NCBI TaxID: {taxid}) from ENA..\n")
        accessions = ena.get_runs(taxid)
        random.shuffle(accessions)
        #if len(accessions) > 2000: #Removed cap on accessions to write in log
            #accessions=accessions[:2000]
            #print(f"Total accessions fetched from ENA: {len(accessions)} (capped)\n")
        #else:    
        print(f"Total accessions fetched from ENA: {len(accessions)}\n")
        #check if there is a previous run in the same outputdir. if so, exit and print error message
        if logfile.contents["Step_1"]["run_info"]["init_time"] is not None:
            if logfile.contents["Step_1"]["status"] == "completed":
                sys.exit(f"Previous completed run detected in {outputdir}. Exiting...")
            else:
                sys.exit(f"Previous incomplete run detected at {outputdir}.\nUse either -con to continue previous run or remove output directory to start a fresh run.\nExiting...")
        
        #check if accessions are given. if not, select accessions from total accessions.
        #check file size.
        if selected_accessions is not None:
            selected_accessions = selected_accessions.split(",")
            print("Checking file sizes of accessions provided by user...")
            selected_accessions_dict={}
            for accession in selected_accessions:
                ascp_fullpath, ftp_fullpath, filesize = aspera.get_download_path_ffq2(accession)
                if sum(filesize) >= filesizelimit:
                    selected_accessions_dict[accession]=(ascp_fullpath,ftp_fullpath,filesize)
                else:
                    print(f"{accession} not included due to insufficient file size.")
                if len(selected_accessions_dict)==n_accessions:
                    break
            if len(selected_accessions_dict)<n_accessions:
                print(f"User-provided accessions are insufficient. Will supplement with other accessions..\nNote: Fetching metadata might take some time.\n")
                for accession in accessions:
                    ascp_fullpath, ftp_fullpath, filesize = aspera.get_download_path_ffq2(accession)
                    if sum(filesize) >= filesizelimit:
                        selected_accessions_dict[accession]=(ascp_fullpath,ftp_fullpath,filesize)
                        print(f"{accession} selected ({len(selected_accessions_dict)}/{n_accessions}).\n")
                        if len(selected_accessions_dict)==n_accessions:
                            break
                if len(selected_accessions_dict)< n_accessions:
                    sys.exit("There are insufficient accessions that fufill file size requirements\nPlease consider decreasing requirement via --filesizelimit argument.\n")
        else:
            print("Selecting accessions with appropriate file sizes to build preliminary assembly...\nNote: Fetching metadata might take some time.\n")
            selected_accessions_dict={}
            for accession in accessions:
                ascp_fullpath, ftp_fullpath, filesize = aspera.get_download_path_ffq2(accession)
                if sum(filesize) >= filesizelimit:
                    selected_accessions_dict[accession]=(ascp_fullpath,ftp_fullpath,filesize)
                    print(f"{accession} selected ({len(selected_accessions_dict)}/{n_accessions}).\n")
                    if len(selected_accessions_dict)==n_accessions:
                        break
            if len(selected_accessions_dict)< n_accessions:
                sys.exit("There are insufficient accessions that fufill file size requirements\nPlease consider decreasing requirement via --filesizelimit argument.\n")
                
        if threadpool % workers != 0:
            print(f"Specified thread pool of {threadpool} is not divisible by number of workers.")
            threadpool= threadpool - (threadpool % workers)
            print(f"Using thread pool of {threadpool} instead.\n")
        threads=int(threadpool/workers)
        
        #write information relavent to fresh run into log file
        logfile.contents["Step_1"]["run_var"]={"taxid":taxid,
        "selected_accessions":selected_accessions_dict,
        "outputdir": outputdir,
        ##"consensus_threshold": consensus_threshold,
        "filesizelimit":filesizelimit,
        "threadpool":threadpool,
        "workers":workers,
        "kmerlen": kmerlen,
        "orfminlen": orfminlen,
        "geneticcode": geneticcode,
        "startcodon": startcodon,
        "download_method":download_method,
        "n_accessions": n_accessions}
        
        logfile.contents["Step_1"]["run_info"]={"taxid":taxid,
        "sci_name": scientific_name, "n_total_acc": len(accessions), "command_issued": " ".join(sys.argv), "init_time": datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
        logfile.contents["Step_1"]["total_acc"]= accessions
        logfile.contents["Step_1"]["processed_acc"]={}
        logfile.update()

    elif conti==True:
        #exit if log file contains command args
        if logfile.contents["Step_1"]["run_info"]["init_time"]==None:
            sys.exit(f"\nNo previous run initiation detected in {outputdir}. Exiting...")
        if logfile.contents["Step_1"]["status"]== "completed":
            sys.exit(f"\nPrevious run initiated in {outputdir} has fully completed. There is nothing to run.")
        #taxid, selected_accessions_dict, outputdir, consensus_threshold, filesizelimit, threadpool, workers, kmerlen , orfminlen, geneticcode, startcodon ,download_method, n_accessions = logfile.contents["Step_1"]["run_var"].values()
        taxid, selected_accessions_dict, outputdir, filesizelimit, threadpool, workers, kmerlen , orfminlen, geneticcode, startcodon ,download_method, n_accessions = logfile.contents["Step_1"]["run_var"].values()
        _, scientific_name, _, command_issued, init_time = logfile.contents["Step_1"]["run_info"].values()
        accessions = logfile.contents["Step_1"].get("total_acc")
        print(f"\nPrevious incomplete run initiated on {init_time} detected:\n{command_issued}\n\nResuming run...\n")
        
        if threadpool % workers != 0:
            threadpool= threadpool - (threadpool % workers)
        threads=int(threadpool/workers)
    
    logfile.load()
    #create temp file to store processed accessions
    pathtoprocessed= os.path.join(outputdir, "Step_1","processed.tsv")
    if not os.path.exists(pathtoprocessed):
        with open(pathtoprocessed, "w") as f:
            f.write("Accession\tn_CDS\n")
    #load tempfile into log file annd update logfile.
    with open(pathtoprocessed, "r") as f:
        logfile.contents["Step_1"]["processed_acc"] = {chunk.split("\t")[0]: chunk.split("\t")[1] for chunk in f.read().split("\n") if chunk != "Accession\tn_CDS" and chunk != ""}
        logfile.contents["Step_1"]["processed_acc"] = {key : value if "failed" in value else int(value) for key, value in logfile.contents["Step_1"]["processed_acc"].items()}
    logfile.update()
    
    #assemble SSAs in parallel
    parallel_ssa(workers)
    with open(pathtoprocessed, "r") as f:
        logfile.contents["Step_1"]["processed_acc"] = {chunk.split("\t")[0]: chunk.split("\t")[1] for chunk in f.read().split("\n") if chunk != "Accession\tn_CDS" and chunk != ""}
        logfile.contents["Step_1"]["processed_acc"] = {key : value if "failed" in value else int(value) for key, value in logfile.contents["Step_1"]["processed_acc"].items()}
    logfile.update()
    #conditional to sense when something is really wrong (i.e. every accession fails)
    if len([k for k in logfile.contents["Step_1"]["processed_acc"].values() if type(k) is int ]) ==0:
        sys.exit("Unexpected error occured. Exiting...")
    ssa_consensus(ssadir)
    logfile.load()
    logfile.contents["Step_1"]["status"]= "completed"
    logfile.update()
    print("LSTrAP-denovo.MakeDraftCDS.py completed.\nGenerating html report...")
    report.generate_from_json_log(logfile.path, os.path.join(outputdir, "LSTrAP-denovo_report.html"))
    
