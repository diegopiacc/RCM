#!/bin/env python

import sys
import platform
import os 
import getpass
import subprocess
import threading


if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
	import pexpect


sys.path.append( os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)) ) , "server"))
import rcm


class SessionThread( threading.Thread ):
    
    threadscount = 0
    
    def __init__ ( self, tunnel_cmd='', vnc_cmd='', passwd = '', otp = '', gui_cmd=None, debug = True ):
        self.debug=debug
        self.tunnel_command = tunnel_cmd
        self.vnc_command = vnc_cmd
        self.gui_cmd=gui_cmd
        self.password = passwd
        self.otp = otp
        threading.Thread.__init__ ( self )
        self.threadnum = SessionThread.threadscount
        SessionThread.threadscount += 1
        if(self.debug): print 'This is thread ' + str ( self.threadnum ) + ' init.'

    def run ( self ):
        if(self.debug):
            print 'This is thread ' + str ( self.threadnum ) + ' run.'
        if(self.gui_cmd): self.gui_cmd(active=True)
        if(self.tunnel_command == ''):
            if(self.debug): print 'This is thread ' + str ( self.threadnum ) + " executing-->" , self.vnc_command.replace(self.password,"****") , "<--"
            #vnc_process=subprocess.Popen(self.vnc_command , bufsize=1, stdout=subprocess.PIPE, shell=True)
            #vnc_process.wait()
            
            child = pexpect.spawn(self.vnc_command) 
            i = child.expect(['Password:', 'standard VNC authentication', 'password:', pexpect.TIMEOUT, pexpect.EOF])
            if i == 2:
                #no certificate
                child.sendline(self.password)
                i = child.expect(['Password:','standard VNC authentication'])
                
            if i == 0:
                # Unix authentication
                child.sendline(self.password)
            elif i == 1:
                # OTP authentication
                child.sendline(self.otp)
            elif i == 3 or i == 4:
                if(self.debug): print "Timeout connecting to the display"
                if(self.gui_cmd): self.gui_cmd(active=False)
                raise Exception("Timeout connecting to the display")
               
            child.expect(pexpect.EOF, timeout=None)           
            if(self.gui_cmd): self.gui_cmd(active=False)
        else:
            if(self.debug): print 'This is thread ' + str ( self.threadnum ) + "executing-->" , self.tunnel_command.replace(self.password,"****") , "<--"
            tunnel_process=subprocess.Popen(self.tunnel_command , bufsize=1, stdout=subprocess.PIPE, stderr=subprocess.PIPE,stdin=subprocess.PIPE, shell=True)
            #tunnel_process.stderr.close()
            tunnel_process.stdin.close()
            while True:
                o = tunnel_process.stdout.readline()
                #print "into the while!-->",o
                if o == '' and tunnel_process.poll() != None: continue
                if(self.debug):
                    print "output from process---->"+o.strip()+"<---"
                if o.strip() == 'pippo' : break
            if(self.debug):
                print "starting vncviewer-->"+self.vnc_command.replace(self.password,"****")+"<--"
            vnc_process=subprocess.Popen(self.vnc_command , bufsize=1, stdout=subprocess.PIPE, stderr=subprocess.PIPE,stdin=subprocess.PIPE, shell=True)
            #vnc_process.stderr.close()
            vnc_process.stdin.close()
            vnc_process.wait()
            if(self.gui_cmd): self.gui_cmd(active=False)




class rcm_client_connection:

    def __init__(self,proxynode='login.plx.cineca.it', user_account='', remoteuser='',password=''):
        self.debug=True
        self.config=dict()
        self.config['ssh']=dict()
        self.config['vnc']=dict()
        self.config['ssh']['win32']=("PLINK.EXE"," -ssh")
        self.config['vnc']['win32']=("vncviewer.exe","")
        self.config['ssh']['linux2']=("ssh")
        self.config['vnc']['linux2']=("vncviewer","")
        self.config['ssh']['darwin']=("ssh")
        self.config['vnc']['darwin']=("vncviewer","")

        if(sys.platform == 'win32'):
          self.config['remote_rcm_server']="module load profile/advanced; module load autoload RCM; python $RCM_HOME/bin/server/rcm_server.py"
        else:
          self.config['remote_rcm_server']="module load profile/advanced; module load autoload RCM 2>/dev/null; python $RCM_HOME/bin/server/rcm_server.py"
        #finding out the basedir, it depends if we are running as executable pyinstaler or as script
        if('frozen' in dir(sys)):
          if(os.environ.has_key('_MEIPASS2')):
            self.basedir = os.path.abspath(os.environ['_MEIPASS2'])
          else:
            self.basedir = os.path.dirname(os.path.abspath(sys.executable))
          self.debug=False
        else:
          self.basedir = os.path.dirname(os.path.abspath(__file__))
            
        #Read file containing the platform on which the client were build
        buildPlatform = os.path.join(self.basedir,"external","build_platform.txt")
        self.buildPlatformString = ""
        if (os.path.exists(buildPlatform)):
            in_file = open(buildPlatform,"r")
            self.buildPlatformString = in_file.read()
            in_file.close()
        
        
        self.sshexe = os.path.join(self.basedir,"external",sys.platform,platform.architecture()[0],"bin",self.config['ssh'][sys.platform][0])
        self.activeConnectionsList = []
        if(self.debug):
            print "uuu", self.sshexe
        if os.path.exists(self.sshexe) :
            self.ssh_command = self.sshexe + self.config['ssh'][sys.platform][1]
        else:
            self.ssh_command = "ssh"
        if(self.debug):
            print "uuu", self.ssh_command
        
        vncexe = os.path.join(self.basedir,"external",sys.platform,platform.architecture()[0],"bin",self.config['vnc'][sys.platform][0])
        if os.path.exists(vncexe):
            self.vncexe=vncexe
        else:
            if(self.debug): print "VNC exec -->",vncexe,"<-- NOT FOUND !!!"
            exit()
        

    def login_setup(self, remoteuser='',password=''):
        self.proxynode='login.plx.cineca.it'
        
        if (remoteuser == ''):
            self.remoteuser=raw_input("Remote user: ")
        else:
            self.remoteuser=remoteuser
        keyfile=os.path.join(self.basedir,'keys',self.remoteuser+'.ppk')
        if(os.path.exists(keyfile)):
            if(sys.platform == 'win32'):
                self.login_options =  " -i " + keyfile + " " + self.remoteuser + "@" + self.proxynode
            else:
                if(self.debug): print "PASSING PRIVATE KEY FILE NOT IMPLEMENTED ON PLATFORM -->"+sys.platform+"<--"
                self.login_options =  " -i " + keyfile + " " + self.remoteuser + "@" + self.proxynode
                
        else:
            if(sys.platform == 'win32'):
                if (password == ''):
                    self.passwd=getpass.getpass("Get password for " + self.remoteuser + "@" + self.proxynode + " : ")
                #    print "got passwd-->",self.passwd
                else:
                    self.passwd=password
                    self.login_options =  " -pw "+self.passwd + " " + self.remoteuser + "@" + self.proxynode
            else:
                if (password == ''):
                    self.passwd=getpass.getpass("Get password for " + self.remoteuser + "@" + self.proxynode + " : ")
                #    print "got passwd-->",self.passwd
                else:
                    self.passwd=password
                    self.login_options =  " " + self.remoteuser + "@" + self.proxynode
        self.ssh_remote_exec_command = self.ssh_command + self.login_options   
        return self.checkCredential() 
        
    def prex(self,cmd):
        fullcommand= self.ssh_remote_exec_command + ' ' + cmd
        if(self.debug):
            print "executing-->",fullcommand.replace(self.passwd,"****")
        if(sys.platform == 'win32'):
            myprocess=subprocess.Popen(fullcommand, bufsize=100000, stdout=subprocess.PIPE, stderr=subprocess.PIPE,stdin=subprocess.PIPE, shell=True)
            myprocess.stdin.close()
            (myout,myerr)=myprocess.communicate()
            myerr=myerr.rsplit("RCM:",1)[0]
            returncode = myprocess.returncode
            if(self.debug):
                print "returned error  -->",myerr
                print "returned output -->",myout
            myprocess.wait()                        
            if(self.debug):
                print "returned        -->",myprocess.returncode
        else:      
            child = pexpect.spawn(fullcommand)
            i = child.expect(['password:', 'RCM:EXCEPTION', pexpect.EOF, pexpect.TIMEOUT])
            if i == 0:
                #no PKI
                child.sendline(self.passwd)
                i = child.expect([pexpect.EOF, 'RCM:EXCEPTION'])
            elif i == 2:
                #use PKI
                pass
            if i == 1: 
                #manage error
                myerr = child.before
                myout =  ''
                returncode = 1
                return (returncode,myout,myerr)
            if i==3:
                raise Exception("Timeout contacting the server")

            myout = child.before
            myout = myout.lstrip()
            myout = myout.replace('\r\n', '\n')        

            child.close()
            returncode = child.exitstatus
            if(self.debug): print "returncode: " + str(returncode)
            returncode = returncode
            myerr = ''
        #find where the real server output starts
        serverOutputString = "server output->"
        index = myout.find(serverOutputString)
        if  index != -1:
            index += len(serverOutputString)
            myout = myout[index:]
            myout = myout.replace('\n', '',1)

        return (returncode,myout,myerr)     

    def list(self):
        (r,o,e)=self.prex(self.config['remote_rcm_server'] + ' ' + 'list')
        if (r != 0):
            if(self.debug): print e
            raise Exception("Server error: {0}".format(e))
        sessions=rcm.rcm_sessions(o)
        if(self.debug):
            sessions.write(2)
        return sessions 
        
    def newconn(self, queue, geometry):
        
#       new_encoded_param=pickle.dumps({'geometry': geometry, 'user_account': self.user_account})
        new_encoded_param='geometry='+ geometry + ' ' + 'queue='+ queue
        (r,o,e)=self.prex(self.config['remote_rcm_server'] + ' ' + 'new' + ' ' + new_encoded_param )
        
        if (r != 0):
            if(self.debug): print e
            raise Exception("Server error: {0}".format(e))
        session=rcm.rcm_session(o)
        return session 

    def kill(self,sessionid):

        (r,o,e)=self.prex(self.config['remote_rcm_server'] + ' ' + 'kill' + ' ' + sessionid)
        
        if (r != 0):
            if(self.debug): print e
            raise Exception("Killling session -> {0} <- failed with error: {1}".format(sessionid, e))
  
    def get_otp(self,sessionid):

        (r,o,e)=self.prex(self.config['remote_rcm_server'] + ' ' + 'otp' + ' ' + sessionid)

        if (r != 0):
            if(self.debug): print e
            raise Exception("Getting OTP passwd session -> {0} <- failed with error: {1}".format(sessionid, e))
            return ''
        else:
            return o.strip()

    def get_version(self):
        (r,o,e)=self.prex(self.config['remote_rcm_server'] + ' ' + 'version' + ' ' + self.buildPlatformString)
        if (r != 0):
            if(self.debug): print e
            raise Exception("Getting last client version failed with error: {0}".format(e))
            return ''
        else:
            return o.split(' ')
        

    def get_queue(self):

        (r,o,e)=self.prex(self.config['remote_rcm_server'] + ' ' + 'queue')
        if(self.debug): print "available queue: ", o

        if (r != 0):
            if(self.debug): print e
            raise Exception("Getting available queue -> {0} <- failed with error: {1}".format(sessionid, e))
            return ''
        else:
            return o.split(' ')
                
    def vncsession(self,session,otp='',gui_cmd=None):
        self.autopass = otp
        portnumber=5900 + int(session.hash['display'])
        if(self.debug): print "portnumber-->",portnumber
        #if(self.autopass == ''):
            #self.autopass=self.get_otp(session.hash['sessionid'])
        if(self.autopass == ''):
            vnc_command=self.vncexe + " -medqual" + " -user " + self.remoteuser
        else:
            if sys.platform == 'win32':
                vnc_command="echo "+self.autopass + " | " + self.vncexe + " -medqual" + " -autopass -nounixlogin"
            else:
                vnc_command = self.vncexe + " -medqual" + " -autopass -nounixlogin"
        if(sys.platform == 'win32'):
            tunnel_command=self.ssh_command  + " -L " +str(portnumber) + ":"+session.hash['node']+":" + str(portnumber) + " " + self.login_options + " echo 'pippo'; sleep 10"
            vnc_command += " localhost:" +str(portnumber)
        else:
            tunnel_command=''
            vnc_command += " -via '"  + self.login_options + "' " + session.hash['node']+":" + session.hash['display']
        SessionThread ( tunnel_command, vnc_command, self.passwd, self.autopass, gui_cmd, self.debug).start()
        
    def checkCredential(self):
        #check user credential 
        #If user use PKI, I can not check password validity
        if(self.debug): print "Checking credentials......"
        try:
            if(sys.platform == 'win32'):
                myprocess=subprocess.Popen("echo yes | " + self.ssh_remote_exec_command, bufsize=100000, stdout=subprocess.PIPE, stderr=subprocess.PIPE,stdin=subprocess.PIPE, shell=True)
                myprocess.stderr.close()
                myprocess.stdin.close()
                #myprocess=subprocess.Popen(self.ssh_remote_exec_command, bufsize=100000, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
                output= ''
                while True:
                    out = myprocess.stdout.read(1)
                    if out == '' and process.poll() != None:
                        break
                    output += out
                    if 'password' in output:
                        return False
                    if 'Welcome to' in output:
                        return True 
            else:      
                ssh_newkey = 'Are you sure you want to continue connecting'
                # my ssh command line
                p=pexpect.spawn(self.ssh_remote_exec_command)
                i=p.expect([ssh_newkey,'password:','Welcome to', pexpect.TIMEOUT])
                if i==0:
                    if(self.debug): print "I say yes"
                    p.sendline('yes')
                    p.expect('password')
                    i = 1            
                if i==1:
                    #send password
                    p.sendline(self.passwd)
                    i=p.expect(['Permission denied', 'Welcome to'],20)
                    if i==0:
                        p.sendline('\r')
                        if(self.debug): print "Permission denied"
                        return False 
                    elif i==1:
                         return True
                elif i==2: #use PKI
                    return True
                if i==3:
                    raise Exception("Timeout checking credential")
                    
        except Exception as e:
            raise Exeception("check credential failed with error: {0}\n".format(e))
            
    
if __name__ == '__main__':
    try:
        
        c = rcm_client_connection()
        c.login_setup()
        c.debug=True
        res=c.list()
        res.write(2)
        newc=c.newconn()
        newsession = newc.hash['sessionid']
        if(self.debug): print "created session -->",newsession,"<- display->",newc.hash['display'],"<-- node-->",newc.hash['node']
        c.vncsession(newc)
        res=c.list()
        res.write(2)
        c.kill(newsession)
        res=c.list()
        res.write(2)
        
        
    except Exception:
        if(self.debug): print "ERROR OCCURRED HERE"
        raise
  