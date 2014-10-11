'''
Created on 10 Oct 2014

@author: dongj3
'''
import unittest
import os
import sys
import logging
sys.path.append('..')
from lib import config
from lib import common_unity
from lib import sp_client
from lib import log_api
from datetime import datetime

class MigrationIMT(unittest.TestCase):
    ''' Base class for all migration test cases
    Initial global variables and setup/cleanup common environment
    '''
    migID=None
    migState=None
    def setUp(self,conf="vdm_destination.cfg"):
        ''' Setup global initialization: 
        1. load global configuration as internal member and pass to child
        2. initial global setting: like logging
        3. create source / destination file systems
        4. set up the migration parameters like thread number, chunk size, etc.
        
        '''
        logging.info('destination setup start:')
        self.conf_name=conf
        self.initial_test()
        self.create_dest_fs()
        self.export_dest_fs()
        self.mount_dest_local_nfs()
        logging.info('destination setup finished!')
        
    def tearDown(self):
        save_flag = False
        logging.debug('destination tear down start:')
    
        if self.is_case_failed():
            logging.warning('Skip tear down to save failure information')
            logging.info('Please check source fs [%s] and destination fs [%s]'
                         , self.cf.src_fs, self.cf.dest_fs)
            
            logging.fatal('FAILED: Case%s %s' % (self.test_id, self.test_name))
            save_flag = True
            #self.save_server_log()
        else:
            logging.fatal('PASSED: Case%s %s' % (self.test_id, self.test_name))
        
        # save test environment if debug flag in config file is set to 2
        '''
        if self.cf.log_level == 2:
            logging.warning('Skip tear down due to debug flag')
            save_flag = True
        '''
        if save_flag: return # if save flag is set, skip the cleanup process and save the test environment
        
        self.umount_local_dst()
        self.deleteShares()
        self.cleanup_dest_fs()
        logging.info('destination tear down finished!')
        
    def testMigBase(self):
        logging.info('#####################################################skip test in order to debug####################################################')
        logging.info('All the test cases will be executed now')
        pass
        logging.info('All the test cases are executed')
	   # self.CreateMigration()
       # self.StopMigration()
       # self.StartMigration()
       # self.DeleteMigration()     
        

    def initial_test(self):
        ''' Setup basic test variables '''
        self.set_test_name_and_id()
        self.load_config()
        self.set_log_config()
        self.setup_log_interface()
        self.spa=sp_client.SPClient('spa', self.cf.spa_ip, self.cf.spa_usr, self.cf.spa_pwd
                                 , self.cf.admin_ip
                                 , self.cf.admin_usr, self.cf.admin_pwd)
        
        if (self.spa.showECOM()):
            self.cf.admin_ip = self.cf.spa_ip
            self.spa=sp_client.SPClient('spa', self.cf.spa_ip, self.cf.spa_usr, self.cf.spa_pwd
                                 , self.cf.admin_ip
                                 , self.cf.admin_usr, self.cf.admin_pwd)
            self.logger.info("Ecom is running on spa and will execute all commands on it")
            self.sp=self.spa
        else:
            self.cf.admin_ip = self.cf.spb_ip
            self.spa=sp_client.SPClient('spa', self.cf.spa_ip, self.cf.spa_usr, self.cf.spa_pwd
                                 , self.cf.admin_ip
                                 , self.cf.admin_usr, self.cf.admin_pwd)
            self.spb=sp_client.SPClient('spb', self.cf.spb_ip, self.cf.spb_usr, self.cf.spb_pwd
                                 , self.cf.admin_ip
                                 , self.cf.admin_usr, self.cf.admin_pwd)
            self.logger.info("Ecom is running on spb and will execute all commands on it")
            self.sp=self.spb
            
    def set_test_name_and_id(self):
        dt = datetime.now()
        self.test_id = '%02d_%02d_%02d_%02d_%02d' % (dt.month, dt.day, dt.hour, dt.minute, dt.second)
        self.test_name = '.'.join(self.id().split('.')[-2:])
    
    def load_config(self):
        self.cf = config.Config(self.conf_name)
        self.cf.load_global_config()
    def set_log_config(self):
        log_api.removeAllLogHandler()
        log_api.setUpStdoutLoggingHandler(logging.DEBUG)
        self.logger = logging.getLogger(__name__)
    
    def setup_log_interface(self):
        #### create logs directory
        log_path = common_unity.scriptsPath() + '/logs/'
        if not os.access(log_path, os.F_OK):
            os.mkdir(log_path)
        log_path = log_path + self.test_id
        if not os.access(log_path, os.F_OK):
            os.mkdir(log_path)
        
        log_file = '%s/%s.log' % (log_path, self.test_name)
        
        while len(logging.root.handlers) > 0:
            logging.root.removeHandler(logging.root.handlers[-1])
            
        logging.root.setLevel(logging.DEBUG)
        
        fh = logging.StreamHandler()
        fmt = logging.Formatter(fmt='%(asctime)s %(levelname)-5s - %(message)s'
                                , datefmt='%m/%d/%Y %H:%M:%S')
        fh.setFormatter(fmt)
        fh.setLevel(self.cf.log_level)
        logging.root.addHandler(fh)
        
        # add file logger
        fh = logging.FileHandler(filename=log_file, mode='w')
        fmt = logging.Formatter(fmt='%(asctime)s %(levelname)-5s - %(message)s'
                                , datefmt='%m/%d/%Y %H:%M:%S')
        fh.setFormatter(fmt)
        # force file handler to output debug level log
        fh.setLevel(logging.DEBUG)
        logging.root.addHandler(fh)
        
        # add result file logger which only record > WARNING
        result_log = '%s/imt_result.log' % (log_path)
        fh = logging.FileHandler(filename=result_log, mode='a')
        fmt = logging.Formatter(fmt='%(asctime)s - %(message)s'
                                , datefmt='%m/%d/%Y %H:%M:%S')
        fh.setFormatter(fmt)
        fh.setLevel(logging.FATAL)
        logging.root.addHandler(fh)
        logging.info('Set up logging interface finish')
        
    def create_dest_fs(self):        
        # create source file system
        self.logger.info('Start to create destination file system')
        (ret, out, err)=self.sp.create64ShareFolder(self.cf.dest_fs,self.cf.sfs_name,self.cf.pool_name,self.cf.dest_fs_size,self.cf.dest_fs_type)
        self.assertEqual(ret, 0, 'Failed to create destination FS %s with %d' % (self.cf.dest_fs,ret))      
       
        
    def export_dest_fs(self):
        # mount file system to /fs_name
        (ret,out, err) = self.sp.createNfsShare(self.cf.sfs_name,self.cf.dest_fs)
        self.assertEqual(ret, 0,'Failed to export %s on %s' % (self.cf.dest_fs,self.cf.sfs_name))
  
        
    def mount_dest_local_nfs(self):
        # mount file system to local dir
        if not os.access(self.cf.local_dest_mnt, os.F_OK): 
            common_unity.mkdir(self.cf.local_dest_mnt)
        (ret,out,err) = common_unity.nfsMount(self.cf.interface, self.cf.dest_fs, self.cf.local_dest_mnt, '-t nfs')
        self.assertEqual(ret, 0, 'NFS mount file system %s failed: %d' % (self.cf.dest_fs, ret))
    def is_case_failed(self):
        ''' Check if case if failed by Assertion or not
        @return: True, failed by assertion. False, not failed by assertion
        '''
        
        import traceback
        test_info = sys.exc_info()
        if test_info[2]:
            tb = traceback.format_exception(test_info[0], test_info[1], test_info[2])
            logging.error(''.join(tb))
            
        #failed = isinstance(test_info[1], AssertionError)
        failed = (test_info[2] != None)
        
            
        return failed
    
    def umount_local_dst(self):
        self.logger.info("Umount destination fs %s on local testing client" % self.cf.dest_fs)
        try:
            common_unity.umount(self.cf.local_dest_mnt)
            common_unity.rmdir(self.cf.local_dest_mnt)          
           
        except:
            self.logger.warning('umount or delete %s' % self.cf.local_nfs_mnt)
        
    def cleanup_dest_fs(self):
        logging.info('Clean up destination file system: %s' % (self.cf.dest_fs))
        
        try:
            self.sp.deleteShareFolder(self.cf.dest_fs)
        except:
            logging.warn('Failed to delete %s' % self.cf.dest_fs)
    
    def deleteShares(self):
        self.sp.deleteNfsShare(self.cf.sfs_name)
    
    def CreateMigration(self):
        logging.info('Create migration for source %s and  destination %s on %s' %(self.cf.src_fs,self.cf.dest_fs,self.cf.sfs_name))
        (self.migID,self.migState)=self.sp.createMigration(self.cf.sfs_name,self.cf.src_fs,self.cf.dest_fs)
        
    def DeleteMigration(self):
        logging.info('Delete mgiration %s for source %s and destination %s on %s' %(self.migID,self.cf.src_fs,self.cf.dest_fs,self.cf.sfs_name))
        self.sp.deleteMigration(self.cf.sfs_name, self.migID)
    def StopMigration(self):
        logging.info('Stop mgiration %s for source %s and destination %s on %s' %(self.migID,self.cf.src_fs,self.cf.dest_fs,self.cf.sfs_name))
        self.sp.stopMigration(self.cf.sfs_name, self.migID)
    def StartMigration(self):
        logging.info('Start mgiration %s for source %s and destination %s on %s' %(self.migID,self.cf.src_fs,self.cf.dest_fs,self.cf.sfs_name))
        self.sp.startMigration(self.cf.sfs_name, self.migID)
    

if __name__ == "__main__":
   
    unittest.main()
      
        
        
        
    
    
    
