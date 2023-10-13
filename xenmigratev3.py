#!/usr/bin/env python
"""
xenmigrate.py
Xen Migrate
Migrate XenServer to Open Source Xen
(c)2011 Jolokia Networks and Mark Pace -- jolokianetworks.com
pace@jolokianetworks.com
AGPL License
USE THIS SOFTWARE AT YOUR OWN RISK!
PLEASE REPORT BUGS SO THEY CAN GET FIXED!

(c)2012 Derek Yang - hswayne77@gmail.com
"""

import gzip
import fnmatch
import os
import subprocess
import sys

def docmd(cmd):
    """
    run a command and return the communicate PIPE
    """
    if debug:
        print('running cmd       :',cmd)
    execute=subprocess.Popen([cmd],shell=True,stdout=subprocess.PIPE)
    return execute.communicate()[0]

def exportvm(vmname,lvdev,destfile,gz=False):
    """
    export lvdev to dest
    """
    if debug:
        print('exporting vm      :',vmuuid)
    # we'll need to handle difference block sizes at some point
    blocksize=1024*1024
    notification=float(2**30) # 2**30=GB
    if gz:
        notification=notification/4
    vmuuid=getvmuuid(vmname)
    vmstatus=getvmstatus(vmuuid)
    if vmstatus=='running':
        cmd='xe vm-shutdown -u root uuid='+vmuuid
        if debug:
            print('halting vm uuid   :',vmuuid)
        docmd(cmd)
    vmstatus=getvmstatus(vmuuid)
    if vmstatus=='halted':
        if not os.path.exists(destfile):
            try:
                print('\nActivating Volume:')
                cmd='lvchange -v -ay '+lvdev
                lvchange=docmd(cmd)
                source=open(lvdev,'rb')
                if gz:
                    dest=gzip.GzipFile(destfile,'wb')
                else:
                    dest=open(destfile,'wb')
                noticetick=notification/(2**30)
                print('\nRW notification every: '+str(noticetick)+'GB')
                notification=notification/blocksize
                sys.stdout.write('Exporting: ')
                write=0
                while True:
                    write=write+1
                    data=source.read(blocksize)
                    if write%notification==0:
                        sys.stdout.write(str((write/notification)*noticetick)+'GBr')
                    if len(data)==0:
                        break #EOF
                    dest.write(data)
                    if write%notification==0:
                        sys.stdout.write('w ')
                    sys.stdout.flush()
                print('\nSuccessful export')
            finally:
                try:
                    source.close()
                    dest.close()
                finally:
                    print('\nDeactivating Volume:')
                    cmd='lvchange -v -an '+lvdev
                    docmd(cmd)
        else:
            print('ERROR: destination file '+destfile+' exists.')
    else:
        print('ERROR: vm status:',vmstatus,'vm needs to be halted to migrate')

def importvm(lvdest,sourcefile,vgdest,lvsize,gz=False):
    """
    import a raw vmfile into a logical volume
    """
    if debug:
        print('importing vm from :',sourcefile)
        print('to logical volume :',lvdest)
        print('on volume group   :',vgdest)
        print('with gz           :',gz)
    blocksize=1024*1024
    notification=float(2**30) # 2**30=GB
    if gz:
        notification=notification/4
    lvexists=0
    lvvgs=getlvdevlist()
    for lvvg in lvvgs:
        if lvdest==lvvg[0]:
            print('ERROR: lv '+lvdest+' exists cannot import')
            lvexists=1
    if not lvexists:
        cmd='lvcreate -v -n '+lvdest+' -L '+lvsize+'G '+vgdest
        print('\nCreating Logical Volume:')
        docmd(cmd)
        try:
            if gz:
                source=gzip.GzipFile(sourcefile,'rb')
            else:
                source=open(sourcefile,'rb')
            destlv='/dev/'+vgdest+'/'+lvdest
            dest=open(destlv,'wb')
            noticetick=notification/(2**30)
            print('\nRW notification every: '+str(noticetick)+'GB')
            notification=notification/blocksize
            sys.stdout.write('Importing: ')
            write=0
            while True:
                write+=1
                data=source.read(blocksize)
                if write%notification==0:
                    sys.stdout.write(str((write/notification)*noticetick)+'GBr')
                if len(data)==0:
                    break # EOF
                dest.write(data)
                if write%notification==0:
                    sys.stdout.write('w ')
                sys.stdout.flush()
            print('\nSuccessful import')
        finally:
            try:
                source.close()
                dest.close()
            finally:
                print()
    else:
        print('ERROR: logical volume '+lvdest+' exists')

def importxenserverdisk(sourcefile,diskuuid,vmuuid,gz=False):
    """
    import disk from sourcefile into xenserver
    """
    if debug:
        print('importing vm from :',sourcefile)
        print('to disk uuid      :',diskuuid)
        print('with gz           :',gz)
    blocksize=1024*1024
    notification=float(2**30) # 2**30=GB
    if gz:
        notification=notification/4
    vmstatus=getvmstatus(vmuuid)
    if vmstatus=='running':
        cmd='xe vm-shutdown -u root uuid='+vmuuid
        if debug:
            print('halting vm uuid   :',vmuuid)
        docmd(cmd)
    vmstatus=getvmstatus(vmuuid)
    if vmstatus=='halted':    
        if os.path.exists(sourcefile):
            try:
                lvdev=getlvdevxen(diskuuid)[0]
                print('to logical volume :',lvdev)
                print('\nActivating Volume:')
                cmd='lvchange -v -ay '+lvdev
                lvchange=docmd(cmd)
                if gz:
                    source=gzip.GzipFile(sourcefile,'rb')
                else:
                    source=open(sourcefile,'rb')
                dest=open(lvdev,'wb')
                noticetick=notification/(2**30)
                print('\nRW notification every: '+str(noticetick)+'GB')
                notification=notification/blocksize
                sys.stdout.write('Importing: ')
                write=0
                while True:
                    write=write+1
                    data=source.read(blocksize)
                    if write%notification==0:
                        sys.stdout.write(str((write/notification)*noticetick)+'GBr')
                    if len(data)==0:
                        break #EOF
                    dest.write(data)
                    if write%notification==0:
                        sys.stdout.write('w ')
                    sys.stdout.flush()
                print('\nSuccessful import')
            finally:
                try:
                    source.close()
                    dest.close()
                finally:
                    print('\nDeactivating Volume:')
                    cmd='lvchange -v -an '+lvdev
                    docmd(cmd)
        else:
            print('ERROR: source file '+sourcefile+' does not exist.')
    else:
        print('ERROR: vm status:',vmstatus,'vm needs to be halted to import disk')


def getdiskuuidvm(diskuuid):
    """
    get vm uuid from disk uuid and return it
    """
    if debug:
        print('vm from disk uuid :',diskuuid)
    cmd='xe vbd-list vdi-uuid='+diskuuid
    response=docmd(cmd).split('vm-uuid ( RO): ')
    vmuuid=response[1].split('\n')[0]
    return vmuuid    

def getlvdevlist():
    """
    get logical volume and volume group list and return it
    """
    lvvgs=[]
    sep=','
    cmd='lvs --separator \''+sep+'\''
    vgdevs=docmd(cmd).split('\n')
    del vgdevs[0]
    del vgdevs[-1]
    for vgdev in vgdevs:
        lv=vgdev.split(sep)[0][2:]
        vg=vgdev.split(sep)[1]
        size=vgdev.split(sep)[3][:-1]
        lvvgs.append([lv,vg,size])
    return lvvgs

def getlvdevxen(vmdiskuuid):
    """
    take the vmdisk uuid and return the logical volume device name
    """
    if debug:
        print('get lv from uuid  :',vmdiskuuid)
    lvvgs=getlvdevlist()
    for lvvg in lvvgs:
        if vmdiskuuid in lvvg[0]:
            lvdev='/dev/'+lvvg[1]+'/'+lvvg[0]
            return lvdev,lvvg[2]
    return None,None

def getvmdiskuuid(vmuuid):
    """
    get the vmdisk uuids from the vmuuid
    return disk uuids in list
    """
    if debug:
        print('disk from uuid    :',vmuuid)
    diskuuid=[]
    cmd='xe vbd-list vm-uuid='+vmuuid
    response=docmd(cmd).split('vdi-uuid ( RO): ')
    del response[0]
    for index,uuid in enumerate(response):
        curuuid=uuid.split('\n')[0]
        if curuuid!='<not in database>':
            partid=uuid.split('\n')[2].split(': ')[1]
            diskuuid.append([curuuid,partid])
    return diskuuid

def getvmstatus(vmuuid):
    cmd='xe vm-list uuid='+vmuuid
    response=docmd(cmd).split('power-state ( RO): ')[1].split('\n')[0]
    return response

def getvmuuid(vmname):
    """
    get the vmuuid from the name-label of a vm
    return uuid
    """
    if debug:
        print('uuid from name    :',vmname)
    try:
        cmd='xe vm-list name-label=\''+vmname+'\''
        uuid=docmd(cmd).split(':')[1].split(' ')[1][:-1]
        return uuid
    except IndexError:
        return 'vm not found'

def reftoraw(refdir,rawfile,gz=False):
    """
    take the ref directory of an xva file and create a raw importable file
    """
    if debug:
        print('ref dir           :',refdir)
        print('to raw file       :',rawfile)
        print('gzip              :',gz)
    blocksize=1024*1024
    notification=float(2**30) # 2**30=GB
    if gz:
        notification=notification/4
    numfiles=0
    for dirobj in os.listdir(refdir):
        try:
            numfile=int(dirobj)
        except ValueError as TypeError:
            numfile=0;
        if numfile>numfiles:
            numfiles=numfile
    print('last file         :',numfiles+1)
    print('disk image size   :',(numfiles+1)/1024,'GB')
    if os.path.isdir(refdir):
        # This may cause problems in Windows!
        if refdir[-1]!='/':
            refdir+='/'
        if not os.path.exists(rawfile):
            try:
                filenum=0
                noticetick=notification/(2**30)
                print('\nRW notification every: '+str(noticetick)+'GB')
                notification=notification/blocksize
                if gz:
                    dest=gzip.GzipFile(rawfile,'wb')
                else:
                    dest=open(rawfile,'wb')
                sys.stdout.write('Converting: ')
                if gz:
                    blankblock=''
                    for loop in range(blocksize):
                        blankblock+='\x00'
                while filenum<=numfiles:
                    if (filenum+1)%notification==0:
                        sys.stdout.write(str(((filenum+1)/notification)*noticetick)+'GBr')
                    filename=str(filenum)
                    while len(filename)<8:
                        filename='0'+filename
                    if os.path.exists(refdir+filename):
                        source=open(refdir+filename,'rb')
                        while True:
                            data=source.read(blocksize)
                            if len(data)==0:
                                source.close()
                                #sys.stdout.write(str('\nProcessing '+refdir+filename+'...'))
                                break # EOF
                            dest.write(data)
                    else:
                        #print '\n'+refdir+filename+' not found, skipping...'
                        if gz:
                            dest.write(blankblock)
                        else:
                            dest.seek(blocksize,1)
                    if (filenum+1)%notification==0:
                        sys.stdout.write('w ')
                    sys.stdout.flush()
                    filenum+=1
                print('\nSuccessful convert')
            finally:
                try:
                    dest.close()
                    source.close()
                finally:
                    print()
        else:
            print('ERROR: rawfile '+rawfile+' exists')
    else:
        print('ERROR: refdir '+refdir+' does not exist')

def vmdktoraw(vmdkfile,rawfile,gz):
    """
    take the ref directory of an xva file and create a raw importable file
    """
    if debug:
        print('vmdk              :',vmdkfile)
        print('to raw            :',rawfile)
        print('gzip              :',gz)
    if (not gz and not os.path.exists(rawfile)) or ((gz and not os.path.exists(rawfile+'.gz')) and (gz and not os.path.exists(rawfile))):
        try:
            cmd='qemu-img convert '+vmdkfile+' -O raw '+rawfile
            print('Converting...')
            response=docmd(cmd)
            print(response)
            if gz:
                cmd='gzip -v '+rawfile
                print('Gzipping...')
                response=docmd(cmd)
            print('Sucessful convert')
        except:
            print('ERROR: problem converting file (do you have qemu-img installed?)')
    else:
        if gz:
            print('ERROR: rawfile '+rawfile+' or '+rawfile+'.gz exists')
        else:
            print('ERROR: rawfile '+rawfile+' exists')
                    
##
## Main Program
##

if __name__=='__main__':
    # globals
    global debug
    debug=False
    # Hello world
    print('xenmigrate 0.7.4 -- 2011.09.13\n(c)2011 Jolokia Networks and Mark Pace -- jolokianetworks.com\n')
    # process arguments
    from optparse import OptionParser
    parser=OptionParser(usage='%prog [-cdhiltvxz] [vmname]|[exportLVdev]|[importVolGroup]|[importdiskuuid]|[converttofile]')
    parser.add_option('-c','--convert',action='store',type='string',dest='convert',metavar='DIR',help='convert DIR or vmdk to importable rawfile')
    parser.add_option('-d','--disk',action='store_true',dest='disk',help='display vm disk uuids',default=False)
    parser.add_option('--debug',action='store_true',dest='debug',help='display debug info',default=False)
    parser.add_option('-i','--import',action='store',type='string',dest='doimport',metavar='FILE',help='import from FILE to [type=xen:importVolGroup]|\n[type=xenserver:importdiskuuid]')
    parser.add_option('-l','--lvdev',action='store_true',dest='lvdev',help='display vm logical volume devices',default=False)
    parser.add_option('-t','--type',action='store',type='string',dest='type',metavar='TYPE',help='import to [xen]|[xenserver]',default='xen')
    parser.add_option('-x','--export',action='store',type='string',dest='export',metavar='FILE',help='export from Xen Server or from Logical Volume dev to FILE')
    parser.add_option('-z','--gzip',action='store_true',dest='gz',help='use compression for import, export, or convert (SLOW!)',default=False)
    (opts,args)=parser.parse_args()    
    if len(args)<1:
        parser.print_help()
        sys.exit(1)
    if opts.debug:
        debug=True
    if opts.disk or opts.lvdev or opts.export:
        vmname=args[0]
        if '/dev' in vmname and opts.export:
            #print 'export dev        :',vmname
            pass
        else:
            vmuuid=getvmuuid(vmname)
            print('vm name-label     :',vmname)
            print('vm uuid           :',vmuuid)
            vmdiskuuids=getvmdiskuuid(vmuuid)
            for vmdiskuuid in vmdiskuuids:
                print('vm disk uuid      :',vmdiskuuid[0])
                print('vm disk partid    :',vmdiskuuid[1])
                if opts.lvdev:
                    lvdev,lvsize=getlvdevxen(vmdiskuuid[0])
                    if lvdev is not None:
                        print('vm disk dev name  :',lvdev)
                        print('vm disk size      :',lvsize+'GB')
                    else:
                        print('vm disk dev name  : not found in mounted storage repositories')
    if opts.export and opts.doimport:
        print('ERROR: export and import cannot be run at the same time')
    elif opts.export and opts.convert:
        print('ERROR: export and convert cannot be run at the same time')
    elif opts.doimport and opts.convert:
        print('ERROR: import and convert cannot be run at the same time')
    elif opts.export and opts.doimport and opts.convert:
        print('ERROR: you have got to be kidding me -- need some more options to run at the same time?')
    elif opts.export:        
        if '/dev' in vmname:
            vmdiskuuids=[vmname]
            # need some logic here to test for logical volume so we don't just blow up
            # we should get the lvsive of the dev 0.7.2 here we come!
            # using type might be a good idea too 0.7.3 probably
        else:
            vmdiskuuids=getvmdiskuuid(vmuuid)
        for vmdiskuuid in vmdiskuuids:
            if '/dev' in vmname:
                lvdev=vmname
                lvsize='xen'
            else:
                lvdev,lvsize=getlvdevxen(vmdiskuuid[0])
            if lvdev is not None:
                exportname=opts.export
                if exportname[-3:]=='.gz':
                    opts.gz=True
                    exportname=exportname[:-3]
                exportname=exportname+'_'+vmdiskuuid[1]+'_'+lvsize
                if opts.gz:
                    exportname=exportname+'.gz'
                print('export dev        :',lvdev)
                print('to raw file       :',exportname)
                if lvdev:
                    exportvm(vmname,lvdev,exportname,opts.gz)
        print('You many need to restart your VM:')
        print('xe vm-startup -u root uuid='+vmuuid)
    elif opts.doimport:
        importname=opts.doimport
        if importname[-3:]=='.gz':
            opts.gz=True
            importname=importname[:-3]
        if opts.type=='xen':
            lvsize=importname.split('_')[-1]
            lvpartid=importname.split('_')[-2]
            lvdesttmp=importname.split('/')[-1]
            for index in range(len(lvdesttmp.split('_'))-2):
                if index==0:
                    lvdest=lvdesttmp.split('_')[0]
                else:
                    lvdest=lvdest+'_'+lvdesttmp.split('_')[index]
            print('import raw file   :',opts.doimport)
            print('to lv             :',lvdest)
            print('in vg             :',args[0])
            print('lv size           :',lvsize+'GB')
            print('xen config partid :',lvpartid)
            importvm(lvdest,opts.doimport,args[0],lvsize,opts.gz)
        elif opts.type=='xenserver':
            print('import raw file   :',opts.doimport)
            print('to disk uuid      :',args[0])
            vmuuid=getdiskuuidvm(args[0])
            print('vm uuid           :',vmuuid)
            importxenserverdisk(opts.doimport,args[0],vmuuid,opts.gz)
        else:
            print('ERROR: unknown Xen type for import')
    elif opts.convert:
        if os.path.isdir(opts.convert):
            print('convert ref dir   :',opts.convert)
            print('to raw file       :',args[0])
            reftoraw(opts.convert,args[0],opts.gz)
        elif os.path.isfile(opts.convert):
            if opts.convert[-5:]=='.vmdk':
                filename=args[0]
                if filename[-3:]=='.gz':
                    opts.gz=True
                    filename=filename[:-3]
                print('convert vmdk file :',opts.convert)
                print('to raw file       :',filename)
                vmdktoraw(opts.convert,filename,opts.gz)
            else:
                print('ERROR: unknown file convert format')
        else:
            print('ERROR: convert source directory or file does not exist')
            sys.exit(1)


