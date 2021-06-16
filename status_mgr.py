#!/usr/bin/python3
import sys,os,json,time,select,random,threading,urllib.request,contextlib
#mgr import curses
from datetime import datetime,timedelta
from collections import namedtuple
from configparser import ConfigParser
import platform,subprocess,re,getopt
import requests,hmac,hashlib,base64
from http.server import BaseHTTPRequestHandler, HTTPServer

peer_blacklist = []
peer_wrong_chain = []
purse_uref = 0;
global_events = dict()
peer_address = None
finality_signatures = []
missing_validators = []
proposers_dict = dict()
our_blocks = dict()
currentProposerBlock = 0
blocks_start = 0
era_rewards_dict = dict()
num_era_rewards = dict()
era_block_start = dict()
our_rewards = []
cpu_usage = []
transfer_dict = dict()
trusted_blocked = []
deploy_dict = dict()
peer_scan_dict = dict()
peer_scan_running = False
peer_scan_last_run = None 
dataJson = {}

PORT = 8080
JSON_FILE='./caspermetrics.json'

import threading
class WebThread(threading.Thread):
    def run(self):
        server = HTTPServer(('', PORT), MyServer)
        server.serve_forever()


class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/casper":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            with open(JSON_FILE, 'r') as f:
                array = json.load(f)
                self.wfile.write(json.dumps(array).encode())
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            value = {
               "error": "Unknown path found"
            }
            self.wfile.write(json.dumps(value).encode()) 


def system_memory():
    global sysmemory
    dataJson['system_memory'] = {}
    #mgr sysmemory = curses.newwin(5, 40, 0, 70)
    #mgr sysmemory.box()
    #mgr box_height, box_width = sysmemory.getmaxyx()
    #mgr text_width = box_width - 17 # length of the Text before it gets printed
    #mgr sysmemory.addstr(0, 2, 'System Memory', curses.color_pair(4))

    MemInfoEntry = namedtuple('MemInfoEntry', ['value', 'unit'])

    meminfo = {}
    with open('/proc/meminfo') as file:
        for line in file:
            key, value, *unit = line.strip().split()
            meminfo[key.rstrip(':')] = MemInfoEntry(value, unit)

    #mgr sysmemory.addstr(1, 2, 'Mem Total  : ', curses.color_pair(1))
    #mgr sysmemory.addstr('{:.2f} GB'.format(float(meminfo['MemTotal'].value)/1024/1024), curses.color_pair(4))
    #mgr sysmemory.addstr(2, 2, 'Mem Avail  : ', curses.color_pair(1))
    #mgr sysmemory.addstr('{:.2f} GB'.format(float(meminfo['MemAvailable'].value)/1024/1024), curses.color_pair(4))
    dataJson['system_memory']['Mem Total'] = float(meminfo['MemTotal'].value)/1024/1024
    dataJson['system_memory']['Mem Avail'] = float(meminfo['MemAvailable'].value)/1024/1024
    mem_total = float(meminfo['MemTotal'].value)
    mem_percent = 100*(mem_total-float(meminfo['MemAvailable'].value))/mem_total

    #mgr sysmemory.addstr(3, 2, 'Mem Used', curses.color_pair(1))
    dataJson['system_memory']['Mem Used'] = mem_percent
    #mgr for x in range(25):
    #mgr     sysmemory.addstr(3,13+x,' ', curses.color_pair(6))
    #mgr for x in range(int(mem_percent/4)):
    #mgr     sysmemory.addstr(3,13+x,' ', curses.color_pair(7+int(mem_percent/25)))

    #mgr sysmemory.addstr(3, 13, '{:.2f} %'.format(mem_percent), curses.color_pair(7+int(mem_percent/25)))


def system_disk():
    global sysdisk
    dataJson['system_disk'] = {}
    #mgr sysdisk = curses.newwin(5, 40, 5, 70)
    #mgr sysdisk.box()
    #mgr box_height, box_width = sysdisk.getmaxyx()
    #mgr text_width = box_width - 17 # length of the Text before it gets printed
    #mgr sysdisk.addstr(0, 2, 'Disk Usage', curses.color_pair(4))

    result=os.statvfs(node_path)
    block_size=result.f_frsize
    total_blocks=result.f_blocks
    free_blocks=result.f_bfree
    # giga=1024*1024*1024
    giga=1000*1000*1000
    total_size=total_blocks*block_size/giga
    free_size=free_blocks*block_size/giga

    #mgr sysdisk.addstr(1, 2, 'Total Disk : ', curses.color_pair(1))
    #mgr sysdisk.addstr('{:.2f} GB'.format(float(total_size)), curses.color_pair(4))
    dataJson['system_disk']['Total Disk'] = float(total_size)
    #mgr sysdisk.addstr(2, 2, 'Free Space : ', curses.color_pair(1))
    #mgr sysdisk.addstr('{:.2f} GB'.format(float(free_size)), curses.color_pair(4))
    dataJson['system_disk']['Free Space'] = float(free_size)
    disk_percent = 100*float(total_size-free_size)/float(total_size)
    dataJson['system_disk']['Disk Used'] = disk_percent
    #mgr sysdisk.addstr(3, 2, 'Disk Used  : ', curses.color_pair(1))

    #mgr for x in range(25):
    #mgr     sysdisk.addstr(3,13+x,' ', curses.color_pair(6))
    #mgr for x in range(int(disk_percent/4)):
    #mgr     sysdisk.addstr(3,13+x,' ', curses.color_pair(7+int(disk_percent/25)))

    #mgr sysdisk.addstr(3, 13, '{:.2f} %'.format(disk_percent), curses.color_pair(7+int(disk_percent/25)))

def get_processor_name():
    if platform.system() == "Windows":
        return platform.processor()
    elif platform.system() == "Darwin":
        os.environ['PATH'] = os.environ['PATH'] + os.pathsep + '/usr/sbin'
        command ="sysctl -n machdep.cpu.brand_string"
        return subprocess.check_output(command).strip()
    elif platform.system() == "Linux":
        command = "cat /proc/cpuinfo"
        all_info = subprocess.check_output(command, shell=True).strip()
        for line in all_info.decode('utf-8').split("\n"):
            if "model name" in line:
                return re.sub( ".*model name.*:", "", line,1)
    return ""

def system_cpu():
    global syscpu
    dataJson['system_cpu'] = {}
    #mgr syscpu = curses.newwin(6, 40, 10, 70)
    #mgr syscpu.box()
    #mgr box_height, box_width = syscpu.getmaxyx()
    #mgr text_width = box_width - 17 # length of the Text before it gets printed
    #mgr syscpu.addstr(0, 2, 'CPU Usage - ', curses.color_pair(4))
    #mgr syscpu.addstr('{} Cores'.format(cpu_cores), curses.color_pair(5))
    #mgr syscpu.addstr(' /', curses.color_pair(4))
    #mgr syscpu.addstr('{}'.format(cpu_name[:14]), curses.color_pair(5))
    dataJson['system_cpu']['CPU Cores'] = cpu_cores
    dataJson['system_cpu']['CPU Name'] = cpu_name[:14]
    result=os.statvfs(node_path)
    block_size=result.f_frsize
    total_blocks=result.f_blocks
    free_blocks=result.f_bfree
    # giga=1024*1024*1024
    giga=1000*1000*1000
    total_size=total_blocks*block_size/giga
    free_size=free_blocks*block_size/giga

    cpu_checks = [1, 300, 3600, 86400]

    index = 1
    for key in cpu_checks:
        m, s = divmod(key, 60)
        h, s = divmod(m, 60)
        d, s = divmod(h, 24)

        interval = '{}{}'.format(d if d > 0 else h if h > 0 else m if m > 0 else key, 'd' if d > 0 else 'h' if h > 0 else 'm' if m > 0 else 's')

        #mgr syscpu.addstr(index, 2, 'Polling {} : '.format(interval), curses.color_pair(1))
        usage = 0
        local_usage = cpu_usage[::-1]
        items = 0
        if len(local_usage) > 0:
            if key == 86400:
                usage = sum(local_usage)
                items = len(local_usage)
            else:
                for cpu in local_usage:
                    usage += cpu
                    items += 1
                    if items >= key:
                        break;

        if usage > 0:
            usage /= items
        #mgr for x in range(25):
        #mgr     syscpu.addstr(index,13+x,' ', curses.color_pair(6))
        #mgr for x in range(int(usage/4)):
        #mgr     syscpu.addstr(index,13+x,' ', curses.color_pair(7+int(usage/25)))

        #mgr syscpu.addstr(index, 13, '{:.2f}%'.format(usage), curses.color_pair(7+int(usage/25)))
        dataJson['system_cpu']['Polling {}'.format(interval)] = '{:.2f}'.format(usage)
#        if len(local_usage) > 0:
#            for i in local_usage:
#                syscpu.addstr('{},'.format(int(i)), curses.color_pair(5))

        index += 1

#    syscpu.addstr(2, 2, 'Free Space : ', curses.color_pair(1))
#    syscpu.addstr('{:.2f} GB'.format(float(free_size)), curses.color_pair(4))

    disk_percent = 100*float(total_size-free_size)/float(total_size)

#    syscpu.addstr(3, 2, 'Disk Used  : ', curses.color_pair(1))

#   for x in range(25):
#       syscpu.addstr(3,13+x,' ', curses.color_pair(6))
#   for x in range(int(disk_percent/4)):
#       syscpu.addstr(3,13+x,' ', curses.color_pair(6+int(disk_percent/25)))

#    syscpu.addstr(3, 13, '{:.2f} %'.format(disk_percent), curses.color_pair(11+int(disk_percent/25)))

def casper_transfers():
    global transfers_view
    dataJson['casper_transfers'] = []
    max_display = 25

    local_events = transfer_dict    # make a copy in case our thread tries to stomp
    length = len(transfer_dict.keys())
    if length > max_display:
        length = max_display
    #mgr transfers_view = curses.newwin(3 + (1 if length < 1 else length), 64, 0, 150)
    #mgr transfers_view.box()
    #mgr box_height, box_width = transfers_view.getmaxyx()
    #mgr text_width = box_width - 17 # length of the Text before it gets printed
    #mgr transfers_view.addstr(0, 2, 'Casper Transfers', curses.color_pair(4))
    #mgr transfers_view.addstr(1, 2, '  Block  / From uref  /  To uref   /         Amount', curses.color_pair(4))

    my_uref = 0 if not purse_uref else purse_uref[5:69]

    items_2_remove = []

    if length < 1:
        mgr='no empty block'
        #mgr transfers_view.addstr(2, 2, 'Waiting for next Transfer', curses.color_pair(5))
        #dataJson['casper_transfers']['Message']='Waiting for next Transfer'
    else:
        index = 1
        for key in list(sorted(local_events.keys(), reverse=True)):
            if index <= max_display:
                transfer = local_events[key]
                #mgr transfers_view.addstr(1+index, 2,'{}'.format(str(transfer[0]).rjust(8, ' ')), curses.color_pair(4))
                #mgr transfers_view.addstr(' / ', curses.color_pair(4))
                source = transfer[2][5:69]
                target = transfer[3][5:69]
                #mgr transfers_view.addstr('{}..{}'.format(source[:4],source[-4:]), curses.color_pair(1 if source != my_uref else 5))
                #mgr transfers_view.addstr(' / ', curses.color_pair(4))
                #mgr transfers_view.addstr('{}..{}'.format(target[:4],target[-4:]), curses.color_pair(1 if target != my_uref else 5))

                #mgr transfers_view.addstr(' / ', curses.color_pair(4))
                amount = int(transfer[1])
                transfer_string = ''
                if (amount > 1000000000):
                    transfer_string = '{:,.4f} CSPR'.format(amount / 1000000000)
                else:
                    transfer_string = '{:,} mote'.format(amount)

                #mgr transfers_view.addstr(transfer_string.rjust(20, ' '), curses.color_pair(5))
                dataJson['casper_transfers'].append({'block' : '{}'.format(str(transfer[0]).rjust(8, ' ')), "From uref" : '{}..{}'.format(source[:4],source[-4:]), "To uref" : '{}..{}'.format(target[:4],target[-4:]), "Amount" : '{}'.format(transfer_string) })

            else:
                items_2_remove.append(key)

            index += 1

        if items_2_remove:
            for key in items_2_remove:
                del transfer_dict[key]

def casper_deploys():
    global deploy_view
    dataJson['casper_deploys'] = []
    #mgr box_height, box_width = peers.getmaxyx()
    #mgr starty = 34+box_height
    max_display = 25

    #mgr max_display = main_height - starty - 3

    length = len(deploy_dict.keys())
    #mgr if length > max_display:
    #mgr     length = max_display

    if len(deploy_dict.keys()) and length < 1:
        length = 1
    if length >= max_display:
        length = max_display

    #mgr box_height, box_width = peers.getmaxyx()
    #mgr deploy_view = curses.newwin(2 + (1 if length < 1 else length), 214, 34+box_height, 0)
    #mgr deploy_view.box()
    #mgr box_height, box_width = deploy_view.getmaxyx()
    #mgr text_width = box_width - 17 # length of the Text before it gets printed
    #mgr deploy_view.addstr(0, 2, 'Casper Deploys', curses.color_pair(4))
    #mgr deploy_view.addstr(0, 178, 'Spent -   Used  =  Overage', curses.color_pair(4))

    if length < 1:
        #mgr deploy_view.addstr(1, 2, 'Waiting for next Deploy', curses.color_pair(5))
        mgr="no empty block"
    else:
        index = 0
        for key in list(sorted(deploy_dict.keys(), reverse=True)):
            deployment = {}
            if index < length:
                deploy = deploy_dict[key]
                deploy_type = deploy[1]
                params = deploy[2]
                name = deploy[3]
                entry = deploy[4]
                result = deploy[5]
                error_message = deploy[6]
                paid_cost = int(deploy[7])
                actual_cost = int(deploy[8])
                timestamp = deploy[9]

                highlight_color = 2 if result == 'Failure' else 5
                base_color = 2 if result == 'Failure' else 4

                #mgr deploy_view.addstr(1+index, 2,'{}'.format(str(deploy[0]).rjust(8, ' ')), curses.color_pair(2 if result == 'Failure' else 4))
                #mgr deploy_view.addstr(' / ', curses.color_pair(4))
                deployment['block']='{}'.format(str(deploy[0]).rjust(8, ' '))
                string = deploy_type
                if len(deploy_type) > 11: 
                    string = '{}..{}'.format(deploy_type[:6], deploy_type[-6:])
                deployment['timestamp'] = timestamp
                #mgr deploy_view.addstr('{}'.format(string.rjust(14,' ')[:14]), curses.color_pair(highlight_color))
                deployment['deploy_type']='{}'.format(string)
                
                if name:
                    #mgr deploy_view.addstr(' / ', curses.color_pair(4))
                    #mgr deploy_view.addstr('{}: '.format('name'.rjust(12,' ')), curses.color_pair(base_color))
                    if name == 'caspersign_contract':
                        name = 'cs_sgn_cntr'
                    #mgr deploy_view.addstr('{}'.format(name.ljust(11, ' ')[:11]), curses.color_pair(highlight_color))
                    deployment['deploy_name']='{}'.format(name)
                if entry:
                    #mgr deploy_view.addstr(' / ', curses.color_pair(4))
                    #mgr deploy_view.addstr('{}: '.format('entry'.rjust(12,' ')), curses.color_pair(base_color))
                    if entry == 'store_signature':
                        entry = 'store_sig'
                    #mgr deploy_view.addstr('{}'.format(entry.ljust(11, ' ')[:11]), curses.color_pair(highlight_color))
                    deployment['deploy_entry']='{}'.format(entry)

                amount = 0
                param_index = 0
                param_area_size = 12
                param_clip = 5
                deployment['deploy_params']=[]

                for param in params:
                    deploymentParam = {}
                    param_index += 1
                    if param_index == 5:
                        param_area_size = 10
                        param_clip = 4

                    if param == 'amount':
                        amount = int(params[param]) / 1000000000
                    else:
                        #mgr deploy_view.addstr(' / ', curses.color_pair(4))
                        string = str(params[param])
                        if param == 'delegation_rate':
                            param = 'd_rate'
                        elif param == 'validator_public_key':
                            param = 'val_pub_key'
                        elif param == 'store_signature':
                            param = 'store_sig'
                        elif len(param) > param_area_size:
                            param = '{}..{}'.format(param[:param_clip], param[-param_clip:])
                        if param_index > 4:
                            mgr='no empty block'
                            #mgr deploy_view.addstr('{}: '.format(param), curses.color_pair(base_color))
                            deploymentParam['key']='{}'.format(param)
                        else:
                            mgr='no empty block'
                            #mgr deploy_view.addstr('{}: '.format(param.rjust(param_area_size,' ')[:param_area_size]), curses.color_pair(base_color))
                            deploymentParam['key']='{}'.format(param.rjust(param_area_size,' ')[:param_area_size])

                        if len(string) > 60:
                            string = '{}..{}'.format(string[:4],string[-4:])
                        elif len(string) > 11:
                            string = '{}..{}'.format(string[:5], string[-4:])
                        if param_index > 4:
                            mgr='no empty block'
                            deploymentParam['value']='{}'.format(string[:11])
                            #mgr deploy_view.addstr('{}'.format(string[:11]), curses.color_pair(highlight_color))
                        else:
                            mgr='no empty block'
                            deploymentParam['value']='{}'.format(string)
                            #mgr deploy_view.addstr('{}'.format(string.ljust(11,' '))[:11], curses.color_pair(highlight_color))
                    deployment['deploy_params'].append(deploymentParam)                   

                if amount and len(params) < 6:
                    #mgr deploy_view.move(1+index,212-41-28-4)
                    #mgr deploy_view.addstr(' / ', curses.color_pair(4))
                    #mgr deploy_view.addstr('amount: ', curses.color_pair(base_color))
                    amount_str = '{:,.2f} CSPR'.format(amount)
                    #mgr deploy_view.addstr('{}'.format(amount_str.rjust(17,' ')[:17]), curses.color_pair(highlight_color))
                    deployment['amount']='{:,.2f} CSPR'.format(amount)

                
                over_under = paid_cost - actual_cost
                if len(params) < 7:
                    #mgr deploy_view.move(1+index,167)
                    if not error_message:
                        paid = '{:,.4f}'.format(paid_cost / 1000000000)[:6]
                        actual = '{:,.4f}'.format(actual_cost / 1000000000)[:6]
                        diff = '{:+,.4f}'.format(over_under / 1000000000)[:6]
                        string = ' / paid: ({} - {}) = {} CSPR'.format(paid, actual, diff)

                        #mgr deploy_view.addstr(' / ', curses.color_pair(4))
                        #mgr deploy_view.addstr('paid: (', curses.color_pair(1))
                        #mgr deploy_view.addstr('{}'.format(paid), curses.color_pair(5))
                        #mgr deploy_view.addstr(' - ', curses.color_pair(4))
                        #mgr deploy_view.addstr('{}'.format(actual), curses.color_pair(5))
                        #mgr deploy_view.addstr(') = ', curses.color_pair(1))
                        #mgr deploy_view.addstr('{} CSPR'.format(diff), curses.color_pair(5))
                        deployment['paid']='{} - {} = {} CSPR'.format(paid, actual, diff)
                    else:
                        mgr='no empty block'
                        #mgr deploy_view.addstr(' / paid: {} {}'.format('{:,.2f}'.format(paid_cost / 1000000000)[:4],error_message[:31]), curses.color_pair(base_color))
                dataJson['casper_deploys'].append(deployment)
            index += 1


def casper_bonds():
    global bonds
    dataJson['casper_bonds'] = {}
    dataJson['casper_bonds']['Infos']={}
    dataJson['casper_bonds']['Previous Rewards']={}
    #mgr bonds = curses.newwin(11, 40, 0, 110)
    #mgr bonds.box()
    #mgr box_height, box_width = bonds.getmaxyx()
    #mgr text_width = box_width - 17 # length of the Text before it gets printed
    #mgr bonds.addstr(0, 2, 'Casper Bond Info', curses.color_pair(4))

    try:
        bids = auction_info['bids']
        for item in bids:
            if item['public_key'].strip("\"") == public_key:
                bond_info = item['bid']
                break

        try:
            staked = float(bond_info['staked_amount'].strip("\""))
        except:
            staked = 0
        try:
            inactive = bond_info['inactive']
        except:
            inactive = False
        try:
            delegation = bond_info['delegation_rate']
        except:
            delegation = 0
        try:
            delegates = bond_info['delegators']
            num_delegates = len(delegates)
        except:
            num_delegates = 0

        try:
            delegate_stake = 0
            for d in delegates:
                delegate_stake += float(d['staked_amount'].strip("\""))
        except:
            delegate_stake = 0

        #mgr bonds.addstr(1, 2, 'Active       : ', curses.color_pair(1))
        if inactive:
            #mgr bonds.addstr('Not Active', curses.color_pair(2 if blink else 20))
            dataJson['casper_bonds']['Infos']['Active'] = 'Not Active'
        else:
            #mgr bonds.addstr('True', curses.color_pair(4))
            dataJson['casper_bonds']['Infos']['Active'] = 'True'


        #mgr bonds.addstr(2, 2, 'Delegation   : ', curses.color_pair(1))
        #mgr bonds.addstr('{} %'.format(delegation), curses.color_pair(4))
        dataJson['casper_bonds']['Infos']['Delegation']='{} %'.format(delegation)

        #mgr bonds.addstr(3, 2, 'Num Delegates: ', curses.color_pair(1))
        #mgr bonds.addstr('{}'.format(num_delegates), curses.color_pair(4))
        dataJson['casper_bonds']['Infos']['Num Delegates']=num_delegates

        our_stake_str = '{:,} CSPR'.format(int(staked / 1000000000))
        delegate_str = '{:,} CSPR'.format(int(delegate_stake / 1000000000))
        total_stake_str = '{:,} CSPR'.format(int((staked + delegate_stake) / 1000000000))

        if (last_val_reward > 1000000000):
            our_reward_str = '{:,} CSPR'.format(int(last_val_reward / 1000000000))
        else:
            our_reward_str = '{:,} mote'.format(int(last_val_reward))

        if (last_del_reward > 1000000000):
            del_reward_str = '{:,} CSPR'.format(int(last_del_reward / 1000000000))
        else:
            del_reward_str = '{:,} mote'.format(int(last_del_reward))

        longest_len = max(len(delegate_str), len(total_stake_str), len(our_reward_str), len(del_reward_str))

        #mgr bonds.addstr(4, 2, 'Auction Bond : ', curses.color_pair(1))
        #mgr bonds.addstr('{}'.format(our_stake_str.rjust(longest_len, ' ')), curses.color_pair(4))
        dataJson['casper_bonds']['Infos']['Auction Bond']='{}'.format(our_stake_str.rjust(longest_len, ' '))

        #mgr bonds.addstr(5, 2, 'Delegate Bond: ', curses.color_pair(1))
        #mgr bonds.addstr('{}'.format(delegate_str.rjust(longest_len, ' ')), curses.color_pair(4))
        dataJson['casper_bonds']['Infos']['Delegate Bond']='{}'.format(delegate_str.rjust(longest_len, ' '))

        #mgr bonds.addstr(6, 2, 'Total Bond   : ', curses.color_pair(1))
        #mgr bonds.addstr('{}'.format(total_stake_str.rjust(longest_len, ' ')), curses.color_pair(4))
        dataJson['casper_bonds']['Infos']['Total Bond']='{}'.format(total_stake_str.rjust(longest_len, ' '))

        #mgr bonds.addstr(7, 2, '--------- Previous Reward ----------', curses.color_pair(5))

        #mgr bonds.addstr(8, 2, 'Validator    : ', curses.color_pair(1))
        reward_percent = last_val_reward/(staked if staked else 1)*12*365
        
        if longest_len > 13:
            #mgr bonds.addstr('{} {:d}%'.format(our_reward_str.rjust(longest_len, ' '),int(reward_percent*100)), curses.color_pair(4))
            dataJson['casper_bonds']['Previous Rewards']['Validator']='{} {:d}%'.format(our_reward_str.rjust(longest_len, ' '),int(reward_percent*100))
        else:
            #mgr bonds.addstr('{} ({:.2%})'.format(our_reward_str.rjust(longest_len, ' '),reward_percent), curses.color_pair(4))
            dataJson['casper_bonds']['Previous Rewards']['Validator']='{} ({:.2%})'.format(our_reward_str.rjust(longest_len, ' '),reward_percent)

        #mgr bonds.addstr(9, 2, 'Delegates    : ', curses.color_pair(1))

        reward_percent = last_del_reward/(delegate_stake if delegate_stake else 1)*12*365
        if longest_len > 13:
            #mgr bonds.addstr('{} {:d}%'.format(del_reward_str.rjust(longest_len, ' '),int(reward_percent*100)), curses.color_pair(4))
            dataJson['casper_bonds']['Previous Rewards']['Delegates']='{} {:d}%'.format(del_reward_str.rjust(longest_len, ' '),int(reward_percent*100))
        else:
            #mgr bonds.addstr('{} ({:.2%})'.format(del_reward_str.rjust(longest_len, ' '),reward_percent), curses.color_pair(4))
            dataJson['casper_bonds']['Previous Rewards']['Delegates']='{} ({:.2%})'.format(del_reward_str.rjust(longest_len, ' '),reward_percent)

    except:
        #mgr bonds.addstr(1, 2, 'No Bond Info Found', curses.color_pair(1))
        dataJson['casper_bonds']['Message']='No Bond Info Found'

class ProposerTask:
    def __init__(self):
        self._running = True

    def terminate(self):
        global_events['terminating'] = 1
        self._running = False

    def run(self):
        loaded1stBlock = False
        global currentProposerBlock
        global blocks_start

        while not loaded1stBlock and self._running:
            time.sleep(1)

            try:
                block_info = json.loads(os.popen('casper-client get-block').read())
                currentProposerBlock = int(block_info['result']['block']['header']['height']) 
                loaded1stBlock = True
            except:
                pass

        # now that we have the 1st block... loop back X blocks to get a brief history
        xBlocks = 700
        lastBlock = currentProposerBlock - xBlocks
        if lastBlock < 1:
            lastBlock = 0
        while currentProposerBlock > lastBlock and self._running:
            try:
                block_info = json.loads(os.popen('casper-client get-block -b {}'.format(currentProposerBlock)).read())
                proposer = block_info['result']['block']['body']['proposer'].strip("\"")
                transfers = block_info['result']['block']['body']['transfer_hashes']
                deploys = block_info['result']['block']['body']['deploy_hashes']

                if proposer in proposers_dict:
                    proposers_dict[proposer] = proposers_dict[proposer] + 1
                else:
                    proposers_dict[proposer] = 1

                if proposer == public_key:
                    era_id = block_info['result']['block']['header']['era_id']
                    if era_id in our_blocks:
                        our_blocks[era_id] = our_blocks[era_id] + 1
                    else:
                        our_blocks[era_id] = 1

                ProcessDeploy(deploys, currentProposerBlock)

                if transfers:
                    transfer = json.loads(os.popen('casper-client get-block-transfers -b {}'.format(currentProposerBlock)).read())
                    transfers = transfer['result']['transfers']
                    block_hash = transfer['result']['block_hash'].strip("\"")
                    root_hash = block_info['result']['block']['header']['state_root_hash']
                    for transfer in transfers:
                        amount = transfer['amount']
                        source = transfer['source'].strip("\"")
                        target = transfer['target'].strip("\"")
                        transfer_dict['{}-{}-{}-{}'.format(str(currentProposerBlock).rjust(8,' '),block_hash,source,target)] = [currentProposerBlock,amount,source,target]

                currentProposerBlock -= 1
                blocks_start = blocks_start + 1
            except:
                global_events['proposer loop error'] = 1
                time.sleep(2)
                pass

def getEraInfo(block, currentEra, update_globals):
    block_info = json.loads(os.popen('casper-client get-era-info-by-switch-block -b {}'.format(block)).read())
    summary = block_info['result']['era_summary']
    if summary != None:
        eraInfo = summary['stored_value']['EraInfo']['seigniorage_allocations']
        currentEra = int(summary['era_id'])
        num_era_rewards[currentEra] = 0
        era_block_start[currentEra] = block

        my_val_reward = 0
        my_del_reward = 0
        
        for info in eraInfo:
            if 'Delegator' in info:
                amount = int(info['Delegator']['amount'])
                if currentEra in era_rewards_dict:
                    era_rewards_dict[currentEra] = era_rewards_dict[currentEra] + amount
                else:
                    era_rewards_dict[currentEra] = amount

                num_era_rewards[currentEra] += 1

                # now check if it was us
                val = info['Delegator']['validator_public_key'].strip("\"")
                if val == public_key:
                    my_del_reward += amount

            elif 'Validator' in info:
                amount = int(info['Validator']['amount'])
                if currentEra in era_rewards_dict:
                    era_rewards_dict[currentEra] = era_rewards_dict[currentEra] + amount
                else:
                    era_rewards_dict[currentEra] = amount
    
                num_era_rewards[currentEra] += 1

                # now check if it was us
                val = info['Validator']['validator_public_key'].strip("\"")
                if val == public_key:
                    my_val_reward += amount

        our_rewards.append(my_val_reward + my_del_reward)

        global last_val_reward
        global last_del_reward
        if update_globals or not last_val_reward:
            last_val_reward = my_val_reward
            last_del_reward = my_del_reward

    return currentEra


class EraTask:
    def __init__(self):
        self._running = True

    def terminate(self):
        global_events['terminating'] = 1
        self._running = False

    def run(self):
        loaded1stBlock = False

        while not loaded1stBlock and self._running:
            time.sleep(1)

            try:
                block_info = json.loads(os.popen('casper-client get-block').read())
                currentBlock = int(block_info['result']['block']['header']['height'])
                currentEra = int(block_info['result']['block']['header']['era_id'])
                era_block_start[currentEra] = currentBlock

                loaded1stBlock = True
            except:
                pass

        # now that we have the current era... loop back X eras to get a brief history
        xEras = 10
        lastEra = currentEra - xEras
        while currentBlock > 0 and currentEra > lastEra and self._running:
            try:
                currentEra = getEraInfo(currentBlock, currentEra, False)
                currentBlock = currentBlock - 1
            except:
                global_events['era loop error'] = 1
                global_events['era block '] = currentBlock

                time.sleep(2)
                pass

def getPeerInfo(ip):
    status = None
    try:
        status = json.loads(os.popen('curl -m 2 -s {}:8888/status'.format(ip)).read())
    except:
        pass

    return status

def getStatusInfo(status,ip):
    try:
        current_api_version = status['api_version']
        current_chain_name = status['chainspec_name']
        last_block_added_info = status['last_added_block_info']
        current_era_id = last_block_added_info['era_id']
        current_height = last_block_added_info['height']
        peer_public_key = status['our_public_signing_key']
        next_upgrade = status['next_upgrade']
        peer_scan_dict[ip] = [peer_public_key,current_api_version,current_chain_name,last_block_added_info,current_era_id,current_height,next_upgrade]
    except:
        pass
    
class ScanValidatorsTask:
    def __init__(self):
        self._running = True

    def terminate(self):
        global_events['terminating'] = 1
        self._running = False

    def run(self):
        global peer_scan_running
        global peer_scan_last_run

        while self._running:
#            start = time.time()

            peer_scan_dict.clear()
            status_not_responding = True
            while status_not_responding:
                try:
                    peers_info = json.loads(os.popen('curl -s {}:8888/status'.format(localhost)).read())
                    status_not_responding = False
                except:
                    time.sleep(2)

            peer_scan_running = True
            getStatusInfo(peers_info,'localhost')
            peers = peers_info['peers']
            for peer in peers:
                address = peer['address']
                ip = address[:address.index(':')]
                status = getPeerInfo(ip)
                if status != None:
                    getStatusInfo(status,ip)
                else:
                    peer_scan_dict[ip] = None

 #           end = time.time()
 #           global_events['scan_time'] = end - start

            peer_scan_running = False
            peer_scan_last_run = datetime.utcnow()

            time.sleep(900)

class PeersTask:
    def __init__(self):
        self._running = True

    def terminate(self):
        global_events['terminating'] = 1
        self._running = False

    def run(self):
        global testing_trusted

        while self._running:
            working = []
            for ip in trusted_blocked:
                status = getPeerInfo(ip)
                if status:
                    working.append(ip)

            not_working = []
            for ip in trusted_ips:
                status = getPeerInfo(ip)
                if not status:
                    not_working.append(ip)

            for ip in working:
                if ip in trusted_blocked:
                    trusted_blocked.remove(ip)
                if ip not in trusted_ips:
                    trusted_ips.append(ip)

            for ip in not_working:
                if ip in trusted_ips:
                    trusted_ips.remove(ip)
                if ip not in trusted_blocked:
                    trusted_blocked.append(ip)

            testing_trusted = False
            time.sleep(300)

def sha265hmac(data, key):
    h = hmac.new(key, data.encode('utf-8'), digestmod=hashlib.sha256)
    return base64.b64encode(h.digest()).decode('utf-8')


class CoinList(object):
    def __init__(self, access_key, access_secret, endpoint_url='https://trade-api.coinlist.co'):
        self.access_key = access_key
        self.access_secret = access_secret
        self.endpoint_url = endpoint_url

    def request(self, method, path, params={}, body={}):
        timestamp = str(int(time.time()))
        # build the request path with any GET params already included
        path_with_params = requests.Request(method, self.endpoint_url + path, params=params).prepare().path_url
        json_body = json.dumps(body, separators=(',', ':')).strip()
        message = timestamp + method + path_with_params + ('' if not body else json_body)
        secret = base64.b64decode(self.access_secret).strip()
        signature = sha265hmac(message, secret)
        headers = {
            'Content-Type': 'application/json',
            'CL-ACCESS-KEY': self.access_key,
            'CL-ACCESS-SIG': signature,
            'CL-ACCESS-TIMESTAMP': timestamp
        }
        url = self.endpoint_url + path_with_params
        r = requests.request(method, url, headers=headers, data=json_body)
        return r.json()

class CpuTask:
    def __init__(self, max_time_interval):
        self._running = True
        self._max_time = int(max_time_interval)

    def terminate(self):
        global_events['terminating'] = 1
        self._running = False

    def run(self):
        last_idle = last_total = 0
        initialized = False
    
        while self._running:
            with open('/proc/stat') as f:
                fields = [float(column) for column in f.readline().strip().split()[1:]]
            idle, total = fields[3], sum(fields)
            idle_delta, total_delta = idle - last_idle, total - last_total
            last_idle, last_total = idle, total
            utilisation = 100.0 * (1.0 - idle_delta / total_delta)
            if not initialized:
                initialized = True
                for _ in range(self._max_time):
                     cpu_usage.append(utilisation)

            cpu_usage.append(utilisation)
            if len(cpu_usage) > self._max_time:
                cpu_usage.pop(0)

            time.sleep(1)

class CoinListTask:
    def __init__(self):
        self._running = True

    def terminate(self):
        global_events['terminating'] = 1
        self._running = False

    def run(self):
        global current_price
        coinlist = CoinList('50883453-345b-4b11-ade9-105ca81c53fd', 'YTxYSY7lXzp7Uq26dXnnPeYSQ2g3JYG1nVP/hmJ9u5eGBS/XXf6OjnnnLr5Nr87GW1upSkVcLDDxxX5hnwaAGA==')

        while self._running:
            try:
                coin_info = coinlist.request('GET', '/v1/symbols/CSPR-USD')
                current_price = coin_info['symbol']['fair_price'][:-4]
            except:
                global_events['price_error'] = 1
                pass

            time.sleep(10)

def ProcessStep(transforms, last_height):
    for transform in transforms:
        if transform['key'].startswith('era-'):
            eraInfo = transform['transform']['WriteEraInfo']['seigniorage_allocations']
            currentEra = int(str(transform['key'])[4:])
            num_era_rewards[currentEra] = 0
            era_block_start[currentEra] = last_height

            my_val_reward = 0
            my_del_reward = 0
            for info in eraInfo:
                if 'Delegator' in info:
                    amount = int(info['Delegator']['amount'])
                    if currentEra in era_rewards_dict:
                        era_rewards_dict[currentEra] = era_rewards_dict[currentEra] + amount
                    else:
                        era_rewards_dict[currentEra] = amount

                    num_era_rewards[currentEra] += 1

                    # now check if it was us
                    val = info['Delegator']['validator_public_key'].strip("\"")
                    if val == public_key:
                        my_del_reward += amount

                elif 'Validator' in info:
                    amount = int(info['Validator']['amount'])
                    if currentEra in era_rewards_dict:
                        era_rewards_dict[currentEra] = era_rewards_dict[currentEra] + amount
                    else:
                        era_rewards_dict[currentEra] = amount

                    num_era_rewards[currentEra] += 1

                    # now check if it was us
                    val = info['Validator']['validator_public_key'].strip("\"")
                    if val == public_key:
                        my_val_reward += amount
                        if (my_val_reward > 1000000000):
                            global_events['Last Reward'] = '{:,.4f} CSPR'.format(my_val_reward / 1000000000)
                        else:
                            global_events['Last Reward'] = '{:,} mote'.format(int(my_val_reward))

         
            if (my_val_reward > 1000000000):
                global_events['Our Last Reward'] = '{:,.4f} CSPR'.format(my_val_reward / 1000000000)
            else:
                global_events['Our Last Reward'] = '{:,} mote'.format(int(my_val_reward))

            if (my_del_reward > 1000000000):
                global_events['Del Last Reward'] = '{:,.4f} CSPR'.format(my_del_reward / 1000000000)
            else:
                global_events['Del Last Reward'] = '{:,} mote'.format(int(my_del_reward))

            our_rewards.append(my_val_reward + my_del_reward)

            last_del_reward = my_del_reward
            last_val_reward = my_val_reward

def ProcessDeploy(deploys, height):
    if deploys:
        for deploy in deploys:
            deploy = deploy.strip("\"")
            d = json.loads(os.popen('casper-client get-deploy {}'.format(deploy)).read())
            payment = d['result']['deploy']['payment']
            session = d['result']['deploy']['session']
            results = d['result']['execution_results'][0]['result']
            result = None
            error_message = None
            actual_cost = 0
            for r in results:
                result = r
                actual_cost = results[r]['cost']
                if result == 'Failure':
                    error_message = results[r]['error_message']
                break

            if session:
                for key in session:
                    if key == 'Transfer' and result != 'Failure':
                        return
                    args = None
                    name = None if 'name' not in session[key] else session[key]['name']
                    entry = None if 'entry_point' not in session[key] else session[key]['entry_point']

                    paid_cost = 0
                    args = payment['ModuleBytes']['args']
                    
                    if args:
                        for arg in args:
                            if arg[0] == 'amount':
                                paid_cost = arg[1]['parsed']

                    args = session[key]['args']
                    if args:
                        params = dict()
                        for arg in args:
                            params[arg[0]] = arg[1]['parsed']

                        deploy_dict['{}-{}'.format(str(height).rjust(8,' '),deploy)] = [height,key,params,name,entry,result,error_message,paid_cost,actual_cost,d['result']['deploy']['header']['timestamp']]
    

class EventTask:
    def __init__(self):
        self._running = True

    def terminate(self):
        global_events['terminating'] = 1
        self._running = False

    def has_finality(self):
        timestamp = datetime.now() - self._time_before_read
        if timestamp.seconds > 10 and 'FinalitySignature' in global_events:
            return True

        return False

    def run(self):
        global localhost
        global round_time
        global avg_rnd_time
        url = 'http://{}:9999/events'.format(localhost)
        localhost_active = False
        while not localhost_active and self._running:
            try:
                self._request = urllib.request.Request(url)
                self._reader = urllib.request.urlopen(self._request)
                localhost_active = True
            except:
                time.sleep(10)

        CHUNK = 6 * 1024
        partial_line = ""
        last_block_time = datetime.utcnow() + timedelta(seconds=65)
        last_height = 0
        StepEvents = False

        try:
            while self._running:
                self._time_before_read = datetime.now()
                try:
                    chunk = self._reader.read(CHUNK)
                    if not chunk:
                        break
                except:
                    break;

                if self.has_finality():
                    global_events['FinalitySignature'] = 0
                    finality_signatures.clear()

                data = chunk.decode().split('\n')
                first = True
                for line in data:
                    if first and len(partial_line):
                        line = '{}{}'.format(partial_line, line)
                        partial_line = ""
 
                    if line.startswith('data:'):
                        try:
                            json_str = json.loads(line[5:])
                            key = list(json_str.keys())[0]
                            if key == 'ApiVersion':
                                global_events[key] = json_str[key]
                                continue
                            if key == 'DeployProcessed':
#                                if not last_height:
#                                    last_height = global_height
#                                deploys = [json_str[key]['deploy_hash']]
#                                ProcessDeploy(deploys, last_height)
                                continue

                            if key == 'Step':
                                StepEvents = True
                                try:
                                    ProcessStep(json_str[key]['execution_effect']['transforms'], last_height)
                                except:
                                    global_events['step_error'] = 1
                                continue

                            if key == 'BlockAdded':
                                round_time = datetime.utcnow()
                                event_time = datetime.strptime(json_str[key]['block']['header']['timestamp'],'%Y-%m-%dT%H:%M:%S.%fZ')
                                last_height = int(json_str[key]['block']['header']['height'])

                                elapsed = event_time - last_block_time
                                if elapsed.total_seconds() < 1:
                                    global_events['Time Since Block'] = 'Calculating'
                                else:
                                    global_events['Time Since Block'] = elapsed
                                    avg_rnd_time = elapsed.total_seconds()

                                last_block_time = event_time

                                if not StepEvents:
                                    try:
                                        era_end = json_str[key]['block']['header']['era_end']
                                        if era_end:
                                            reward = era_end['era_report']['rewards']['{}'.format(public_key)]
                                            if (reward > 1000000000):
                                                global_events['Last Reward'] = '{:,.4f} CSPR'.format(reward / 1000000000)
                                            else:
                                                global_events['Last Reward'] = '{:,} mote'.format(int(reward))
                                    except:
                                        global_events['Last Reward'] = 'Not Found'

                                try:
                                    proposer = json_str[key]['block']['body']['proposer'].strip("\"")
                                    if proposer in proposers_dict:
                                        proposers_dict[proposer] = proposers_dict[proposer] + 1
                                    else:
                                        proposers_dict[proposer] = 1

                                    if proposer == public_key:
                                        era_id = json_str[key]['block']['header']['era_id']
                                        if era_id in our_blocks:
                                            our_blocks[era_id] = our_blocks[era_id] + 1
                                        else:
                                            our_blocks[era_id] = 1
                                except:
                                    global_events['proposer_error'] = 1
                                    pass

#                                try:
#                                    deploys = json_str[key]['block']['body']['deploy_hashes']
#                                    ProcessDeploy(deploys, last_height)
#                                except:
#                                    pass

#                                try:
#                                    transfer_hashs = json_str[key]['block']['body']['transfer_hashes']
#                                    if transfer_hashs:
#                                        if 'Transfers' in global_events:
#                                            global_events['Transfers'] = global_events['Transfers'] + len(transfer_hashs)
#                                        else:
#                                            global_events['Transfers'] = len(transfer_hashs)
#                                except:
#                                    pass

                                try:
                                    era_id = json_str[key]['block']['header']['era_id']

                                    if last_height:
                                        getEraInfo(last_height, era_id, True)
                                except:
                                    pass


                            try:
                                if key == 'FinalitySignature':
                                    pub_key = json_str[key]['public_key'].strip("\"")
                                    finality_signatures.append(pub_key)
                                    continue
                            except:
                                pass


                            if key in global_events:
                                global_events[key] = global_events[key] + 1
                            else:
                                global_events[key] = 1
                        except:
                            partial_line = line

            global_events['exiting'] = 1
        except (KeyboardInterrupt, SystemExit):            
            global_events['except'] = 1


def casper_events():
    global events
    dataJson['casper_events'] = {}
    #mgr events_box_y, events_box_x = proposers.getbegyx()
    #mgr events_box_height, events_box_width = proposers.getmaxyx()

    local_events = global_events    # make a copy in case our thread tries to stomp
    num_events = len(local_events.keys())
    length = num_events

    #mgr events = curses.newwin(2 + 5, events_box_width, events_box_y+events_box_height, events_box_x)
    #mgr events.box()
    #mgr box_height, box_width = events.getmaxyx()
    #mgr text_width = box_width - 17 # length of the Text before it gets printed
    #mgr events.addstr(0, 2, 'Casper Events', curses.color_pair(4))

    skip_list = ['BlockAdded', 'DeployProcessed', 'FinalitySignature', 'Time Since Block', 'Last Reward']
    
    if length < 1:
        #mgr events.addstr(1, 2, 'Waiting for next Event', curses.color_pair(5))
        dataJson['casper_events']['Message'] = 'Waiting for next Event'
    else:
        index = 0
        skipped = []
        for key in list(sorted(local_events.keys())):
            if num_events > 5 and key in skip_list:
                skipped.append(key)
                continue
            #mgr events.addstr(1+index, 2, '{} : '.format(key.ljust(17, ' ')), curses.color_pair(1))
            #mgr events.addstr('{}'.format(local_events[key]), curses.color_pair(4))
            dataJson['casper_events']['{}'.format(key.ljust(17, ' '))] ='{}'.format(local_events[key])
            index += 1 
            if index >= 5:
                break

        if index < 5:
            for key in skipped:
                #mgr events.addstr(1+index, 2, '{} : '.format(key.ljust(17, ' ')), curses.color_pair(1))
                #mgr events.addstr('{}'.format(local_events[key]), curses.color_pair(4))
                dataJson['casper_events']['{}'.format(key.ljust(17, ' '))] ='{}'.format(local_events[key])
                index += 1
                if index >= 5:
                    break



def casper_proposers():
    global proposers
    dataJson['casper_proposers'] = {}
    local_proposers = proposers_dict    # make a copy in case our thread tries to stomp

    max_proposers = 21
    we_are_included = False
    for proposer in sorted(local_proposers.items(), key=lambda x: x[1], reverse=True):
        if proposer[0] == public_key:
            we_are_included = True
            break

    length = min(len(local_proposers.keys()), max_proposers)
    window_length = length + (0 if we_are_included else 1)

    #mgr bonds_y, bonds_x = bonds.getmaxyx()
    #mgr proposers= curses.newwin(2 + max_proposers, 40, bonds_y, 110)

    #mgr proposers.box()
    #mgr box_height, box_width = proposers.getmaxyx()
    #mgr text_width = box_width - 17 # length of the Text before it gets printed
    #mgr proposers.addstr(0, 2, 'Last', curses.color_pair(4))
    #mgr proposers.addstr(' {:6} '.format((global_height-currentProposerBlock) if global_height > 0 and currentProposerBlock > 0 else 0), curses.color_pair(5))
    #mgr proposers.addstr('Blks / Stk Wgt / Prpsr %', curses.color_pair(4))

    dataJson['casper_proposers']['last_blocks']='{:6}'.format((global_height-currentProposerBlock) if global_height > 0 and currentProposerBlock > 0 else 0)
    dataJson['casper_proposers']['proposers'] = []
    index = 1
    try:
        blocks = global_events['BlockAdded'] + blocks_start
    except:
        blocks = 1 if blocks_start < 1 else blocks_start

    try:
        if not length:
            mgr='no empty block'
            #mgr proposers.addstr(index, 2, 'Waiting for next Event', curses.color_pair(5))
        else:
            total_staked = 0
            for item in current_weights.items():
                total_staked += item[1] 

            we_are_included = False
            for proposer in sorted(local_proposers.items(), key=lambda x: x[1], reverse=True):
                p = {}
                if index == max_proposers and not we_are_included and proposer[0] != public_key:
                    continue

                #mgr proposers.addstr(index, 2, '{}....{} : '.format(proposer[0][:6], proposer[0][-6:]), curses.color_pair(1 if proposer[0] != public_key else 5))
                #mgr proposers.addstr('{:6.2f}%'.format(current_weights[proposer[0]]/total_staked*100), curses.color_pair(4))
                #mgr proposers.addstr(' / ', curses.color_pair(1))
                #mgr proposers.addstr('{:6.2f}%'.format(100*proposer[1]/blocks), curses.color_pair(4))
                p["public_key"]='{}....{}'.format(proposer[0][:6], proposer[0][-6:])
                p["stake_weight"]='{:6.2f}%'.format(current_weights[proposer[0]]/total_staked*100)
                p["proposer_percentage"]= '{:6.2f}%'.format(100*proposer[1]/blocks)
               
                
                index += 1

                if proposer[0] == public_key:
                    we_are_included = True
                    d['me']=True
                dataJson['casper_proposers']['proposers'].append(p)
                if index > max_proposers:
                    break


            if not we_are_included and public_key in current_weights:            
                #proposers.addstr(index, 2, '{}....{} : '.format(public_key[:6], public_key[-6:]), curses.color_pair(5))
                if public_key in local_proposers:
                    #mgr proposers.addstr('{:6.2f}%'.format(current_weights[public_key]/3500000000000000000*100), curses.color_pair(4))
                    #mgr proposers.addstr(' / ', curses.color_pair(1))
                    #mgr proposers.addstr('{:6.2f}%'.format(100*local_proposers[public_key]/blocks), curses.color_pair(4))
                    p={
                    "public_key" : '{}....{}'.format(proposer[0][:6], proposer[0][-6:]),
                    "stake_weight" : '{:6.2f}%'.format(current_weights[public_key]/3500000000000000000*100),
                    "proposer_percentage" : '{:6.2f}%'.format(100*local_proposers[public_key]/blocks)
                    }
                    dataJson['casper_proposers']['proposers'].append(p)
                else:
                    #mgr proposers.addstr('{:6.2f}%'.format(current_weights[public_key]/3500000000000000000*100), curses.color_pair(4))
                    #mgr proposers.addstr(' / ', curses.color_pair(1))
                    #mgr proposers.addstr('{:6.2f}%'.format(0), curses.color_pair(4))
                    p={
                    "public_key" : '{}....{}'.format(proposer[0][:6], proposer[0][-6:]),
                    "stake_weight" : '{:6.2f}%'.format(current_weights[public_key]/3500000000000000000*100),
                    "proposer_percentage" : '{:6.2f}%'.format(0)
                    }
                    dataJson['casper_proposers']['proposers'].append(p)
    except:
        pass

def casper_era_rewards():
    dataJson['casper_era_rewards'] = {}
    dataJson['casper_era_rewards']['rewards'] = {}
    dataJson['casper_era_rewards']['blocks'] = {}
    global era_rewards

    #mgr events_box_y, events_box_x = syscpu.getbegyx()
    #mgr events_box_height, events_box_width = syscpu.getmaxyx()

    max_print = 10

    length = min(len(era_rewards_dict), max_print)
    #mgr era_rewards = curses.newwin(2 + (max_print*2)+2, events_box_width, events_box_y+events_box_height, events_box_x)

    #mgr era_rewards.box()
    #mgr box_height, box_width = era_rewards.getmaxyx()
    #mgr text_width = box_width - 17 # length of the Text before it gets printed
    #mgr era_rewards.addstr(0, 2, 'Average Era Rewards / Blocks', curses.color_pair(4))

    current_print = 0
    index = 1
    for era in sorted(era_rewards_dict.items(), key=lambda x: x[0], reverse=True):
        #mgr era_rewards.addstr(index, 2, '{} Reward : '.format(era[0]), curses.color_pair(1))
        #mgr era_rewards.addstr('{:10,.4f} CSPR'.format((era[1]/num_era_rewards[era[0]]) / 1000000000), curses.color_pair(4))
        dataJson['casper_era_rewards']['rewards']['Era {}'.format(era[0])]='{:10,.4f} CSPR'.format((era[1]/num_era_rewards[era[0]]) / 1000000000)
        index += 1
        current_print += 1

        if current_print >= max_print:
            break

    #mgr era_rewards.addstr(index, 2, '--------', curses.color_pair(5))
    index += 1

    current_print = 0
    for era in sorted(era_block_start.items(), key=lambda x: x[0], reverse=True):
        diff = 0
        next_era = era[0]-1

        if next_era in era_block_start:
            diff = era[1] - era_block_start[next_era]

        if diff != 0:
            #mgr era_rewards.addstr(index, 2, '{} Blocks : '.format(era[0]), curses.color_pair(1))
            #mgr era_rewards.addstr('{:5}'.format(diff), curses.color_pair(4))
            dataJson['casper_era_rewards']['blocks']['Era {}'.format(era[0])]='{:5}'.format(diff)
            index += 1
            current_print += 1

        if current_print >= max_print:
            break


def casper_finality():
    global finality
    dataJson['casper_finality'] = {}
    local_events = global_events    # make a copy in case our thread tries to stomp
    length = len(local_events.keys())
    starty = 18+ 2 + (1 if length < 1 else length)

    missing_val = len(missing_validators)

    #mgr finality= curses.newwin(2 + (1 if missing_val < 1 else missing_val), 40, starty, 70)

    #mgr finality.box()
    #mgr box_height, box_width = finality.getmaxyx()
    #mgr text_width = box_width - 17 # length of the Text before it gets printed
    #mgr finality.addstr(0, 2, 'Validators Not Finalized', curses.color_pair(4))
    
    index = 1
    if not len(missing_validators):
        mgr='no empty block'
        #mgr finality.addstr(index, 2, 'Checking Finality Signatures' if length > 0 else 'Waiting for next Event', curses.color_pair(5))
    else:
        for missing in missing_validators:
            #mgr finality.addstr(index, 2, '{}....{}'.format(missing[:16], missing[-16:]), curses.color_pair(1 if missing != public_key else 2 if blink else 20))
            index = index + 1


def casper_peers():
    global peers
    dataJson['casper_peers'] = {}
    #mgr peers = curses.newwin(6, 70, 34, 0)
    #mgr peers.box()
    #mgr box_height, box_width = peers.getmaxyx()
    #mgr text_width = box_width - 17 # length of the Text before it gets printed
    #mgr peers.addstr(0, 2, 'Casper Peers - ', curses.color_pair(4))

    if peer_scan_running:
        mgr='no empty block'
        #mgr peers.addstr('Scanning Peers', curses.color_pair(5))
    elif peer_scan_last_run != None:
        elapsed = 900 - (datetime.utcnow() - peer_scan_last_run).total_seconds()
        minutes = int(elapsed / 60)
        seconds = int(elapsed % 60)
        #mgr peers.addstr('Next scan in ~{}m {:02}s'.format(minutes, seconds), curses.color_pair(5))
    else:
        mgr='no empty block'
        #mgr peers.addstr('Waiting to Scan', curses.color_pair(5))

    try:
        num_peers = len(local_status['peers'])
    except:
        num_peers = 0

    #mgr peers.addstr(1, 2, 'Peers   : ', curses.color_pair(1))
    #mgr peers.addstr('{}'.format(num_peers), curses.color_pair(4))
    dataJson['casper_peers']['Peers']=num_peers
    #mgr peers.addstr(2, 2, 'Trusted : ', curses.color_pair(1))
    if not testing_trusted:
        #mgr peers.addstr('{}'.format(len(trusted_ips)), curses.color_pair(4))
        #mgr peers.addstr(2, 20, '->', curses.color_pair(1))
        #mgr peers.addstr(2, 25, 'Closed    : ', curses.color_pair(1))
        #mgr peers.addstr('{}'.format(len(trusted_blocked)), curses.color_pair(4))
        dataJson['casper_peers']['Closed']=len(trusted_blocked)
    else:
        mgr = "no empty block"
        #mgr peers.addstr('Testing', curses.color_pair(5))

    #mgr peers.addstr(2, 42, 'Total Trusted : ', curses.color_pair(1))
    #mgr peers.addstr('{}'.format(len(trusted_ips)+len(trusted_blocked)), curses.color_pair(4))
    dataJson['casper_peers']['Total Trusted']=len(trusted_ips)+len(trusted_blocked)
    local_peer_scan_dict = peer_scan_dict.copy()
    peers_total = len(local_peer_scan_dict.keys())
    peers_blocked = 0
    peers_wrong_chain = 0
    peers_wrong_version = 0
    peers_not_upgraded = 0
    we_have_not_staged = False
    missing_era_upgrade = 0
    our_era_upgrade = 0

    if peers_total:
        our_peer = local_peer_scan_dict['localhost']
        our_chain = our_peer[2]
        our_version = our_peer[1]
        our_next_upgrade = our_peer[6]
        if our_next_upgrade != None:
            our_era_upgrade = int(our_next_upgrade['activation_point'])
            our_upgrade = our_next_upgrade['protocol_version']

        total_staked = 0
        for item in current_weights.items():
            total_staked += item[1]
        
        peers_staked = 0

        for ip in local_peer_scan_dict:
            current_peer = local_peer_scan_dict[ip]
            if current_peer == None:
                peers_blocked += 1
            else:
                peer_key = current_peer[0]
                if peer_key in current_weights:
                    peers_staked += current_weights[peer_key]
                if our_chain != current_peer[2]:
                    peers_wrong_chain += 1
                elif our_version != current_peer[1]:
                    peers_wrong_version += 1
                peer_next_upgrade = current_peer[6]
                if peer_next_upgrade != None:
                    peer_era_upgrade = int(peer_next_upgrade['activation_point'])
                    peer_upgrade = peer_next_upgrade['protocol_version']
                    if current_era_global < peer_era_upgrade:
                        we_have_not_staged = True
                        missing_era_upgrade = peer_era_upgrade
                if peer_next_upgrade != our_next_upgrade:
                    peers_not_upgraded += 1

        #mgr peers.addstr(3, 2, 'Blocked : ', curses.color_pair(1))
        #mgr peers.addstr('{:.2%} ({})'.format(peers_blocked/peers_total, peers_blocked), curses.color_pair(4))
        dataJson['casper_peers']['Blocked']='{:.2%} ({})'.format(peers_blocked/peers_total, peers_blocked)

        #mgr peers.addstr(3, 25, 'Bad Chain : ', curses.color_pair(1))
        #mgr peers.addstr('{:.2%} ({})'.format(peers_wrong_chain/peers_total, peers_wrong_chain), curses.color_pair(4))
        dataJson['casper_peers']['Bad Chain']='{:.2%} ({})'.format(peers_wrong_chain/peers_total, peers_wrong_chain)

        #mgr peers.addstr(3, 48, 'Bad Ver : ', curses.color_pair(1))
        #mgr peers.addstr('{:.2%} ({})'.format(peers_wrong_version/peers_total,peers_wrong_version), curses.color_pair(4))
        dataJson['casper_peers']['Bad Ver']='{:.2%} ({})'.format(peers_wrong_version/peers_total,peers_wrong_version)

        if we_have_not_staged:
            #mgr peers.addstr(4, 2, 'It appears someone has an upgrade staged for', curses.color_pair(5))
            #mgr peers.addstr(' {} '.format(missing_era_upgrade), curses.color_pair(1))
            #mgr peers.addstr('and we do not!', curses.color_pair(5))
            dataJson['casper_peers']['Message']='It appears someone has an upgrade staged for {} and we do not!'.format(missing_era_upgrade)
        elif total_staked:
            #mgr peers.addstr(4, 25, 'Stk Weight: ', curses.color_pair(1))
            #mgr peers.addstr('{:.2%}'.format(peers_staked/total_staked), curses.color_pair(4))
            dataJson['casper_peers']['Stk Weight']='{:.2%}'.format(peers_staked/total_staked)
#            if True:
            if our_next_upgrade == None:
                #mgr peers.addstr(4, 2, 'Answring: ', curses.color_pair(1))
                #mgr peers.addstr('{:.2%} ({})'.format((peers_total - peers_blocked - peers_not_upgraded)/peers_total, peers_total - peers_blocked), curses.color_pair(4))
                dataJson['casper_peers']['Answring']='{:.2%} ({})'.format((peers_total - peers_blocked - peers_not_upgraded)/peers_total, peers_total - peers_blocked)
            else:
                #mgr peers.addstr(4, 2, 'Staged  : ', curses.color_pair(1))
                #mgr peers.addstr('{:.2%} ({})'.format((peers_total - peers_blocked - peers_not_upgraded)/peers_total, peers_total - peers_blocked), curses.color_pair(4))
                dataJson['casper_peers']['Staged']='{:.2%} ({})'.format((peers_total - peers_blocked - peers_not_upgraded)/peers_total, peers_total - peers_blocked)

                #mgr peers.addstr(4, 48, 'Not Stgd: ', curses.color_pair(1))
                #mgr peers.addstr('{:.2%} ({})'.format(peers_not_upgraded/peers_total, peers_not_upgraded), curses.color_pair(4))
                dataJson['casper_peers']['Not Stgd']='{:.2%} ({})'.format(peers_not_upgraded/peers_total, peers_not_upgraded)

def casper_launcher():
    global launcher
    dataJson['casper_launcher'] = {}
    #mgr launcher = curses.newwin(7, 70, 0, 0)
    #mgr launcher.box()
    #mgr box_height, box_width = launcher.getmaxyx()
    #mgr text_width = box_width - 17 # length of the Text before it gets printed
    #mgr launcher.addstr(0, 2, 'Casper Node Launcher', curses.color_pair(4))

    key_value = os.popen('systemctl show casper-node-launcher.service | grep -e MemoryCurrent -e ActiveState -e LoadState -e FragmentPath -e StateChangeTimestamp=').read().split('\n')
    json_dict = {}
    for entry in key_value:
        kv = entry.split("=", 1)
        if len(kv) == 2:
            json_dict[kv[0]] = kv[1]

    index = 1;

    try:
        memory = json_dict['MemoryCurrent']
    except:
        memory = 'null'
    try:
        active = json_dict['ActiveState']
    except:
        active = 'null'
    try:
        load = json_dict['LoadState']
    except:
        load = 'null'
    try:
        fragment = json_dict['FragmentPath']
    except:
        fragment = 'null'
    try:
        timestamp = json_dict['StateChangeTimestamp']
        target = datetime.strptime(timestamp,'%a %Y-%m-%d %H:%M:%S %Z')
        now = datetime.now()
        timestamp = now - target
    except:
        timestamp = 'null'

    global has_been_active
    if active == 'active':
        has_been_active = True
        #mgr launcher.addstr(1, 2, 'MemoryCurrent: ', curses.color_pair(1))
        #mgr launcher.addstr('{}'.format(memory), curses.color_pair(4))
        dataJson['casper_launcher']['MemoryCurrent'] = memory

        #mgr launcher.addstr(2, 2, 'ActiveState  : ', curses.color_pair(1))
        #mgr launcher.addstr('{}'.format(active), curses.color_pair(4))
        dataJson['casper_launcher']['ActiveState'] = active

        #mgr launcher.addstr(3, 2, 'LoadState    : ', curses.color_pair(1))
        #mgr launcher.addstr('{}'.format(load), curses.color_pair(4))
        dataJson['casper_launcher']['LoadState'] = load
    
        #mgr launcher.addstr(4, 2, 'FragmentPath : ', curses.color_pair(1))
        #mgr launcher.addstr('{}'.format(fragment), curses.color_pair(4))
        dataJson['casper_launcher']['FragmentPath'] = fragment

        #mgr launcher.addstr(5, 2, 'Running Time : ', curses.color_pair(1))
        #mgr launcher.addstr('{}'.format(timestamp), curses.color_pair(4))
        dataJson['casper_launcher']['Running Time'] = format(timestamp)
    else:
        if has_been_active:
            os.execv(sys.argv[0], sys.argv)
        #mgr launcher.addstr(1, 2, 'Casper-Node-Launcher not running', curses.color_pair(2))
        dataJson['casper_launcher']['ActiveState'] = 'Casper-Node-Launcher not running'



def casper_block_info():
    global block_info
    global global_height
    dataJson['casper_block_info'] = {}
    #mgr block_info = curses.newwin(15, 70, 7, 0)
    #mgr block_info.box()
    #mgr box_height, box_width = block_info.getmaxyx()
    #mgr text_width = box_width - 17 # length of the Text before it gets printed
    #mgr block_info.addstr(0, 2, 'Casper Block Info', curses.color_pair(4))

    global local_status
    local_status = 'null'

    global local_chainspec
    local_chainspec = 'null'

    next_era_upgrade = 0
    try:
        local_status = json.loads(os.popen('curl -s {}:8888/status'.format(localhost)).read())
        local_chainspec = local_status['chainspec_name']

        last_added_block_info = local_status['last_added_block_info']
        try:
            global_height = local_height = last_added_block_info['height']
        except:
            global_height = 0
            local_height = 'null'
        try:
            round_length = local_status['round_length']
        except:
            round_length = 'null'
        try:
            next_upgrade = local_status['next_upgrade']
            if next_upgrade != None:
                next_era_upgrade = int(next_upgrade['activation_point'])
                next_upgrade = 'Version: {}'.format(next_upgrade['protocol_version'])
        except:
            next_upgrade = None
        try:
            build_version = local_status['build_version']
        except:
            build_version = 'null'
        try:
            chain_name = local_status['chainspec_name']
        except:
            chain_name = 'null'
        try:
            root_hash = local_status['starting_state_root_hash']
        except:
            root_hash = 'null'
        try:
            api_version = local_status['api_version']
        except:
            api_version = 'null'
        try:
            local_era = last_added_block_info['era_id']
        except:
            local_era = 'null'
    except:
        global_height = 0
        local_height = 'null'
        round_length = 'null'
        next_upgrade = None
        build_version= 'null'
        chain_name = 'null'
        root_hash = 'null'
        api_version = 'null'
        local_era = 'null'
        local_chainspe = 'null'

    global peer_address
    previous_peer = peer_address

    try:
        peer_to_use_as_global = random.choice(local_status['peers'])
        peer_address = peer_to_use_as_global['address'].split(':')[0]
        if peer_address in peer_blacklist or peer_address in peer_wrong_chain:
            peer_address = previous_peer
    except:
        try:
            peer_address = random.choice(trusted_ips)
        except:
            peer_address = previous_peer

    if peer_address:
        try:
            try:
                peer_status = json.loads(os.popen('curl -m 2 -s {}:8888/status'.format(peer_address)).read())
                peer_chainspec = peer_status['chainspec_name']
                if peer_chainspec != local_chainspec:
                    peer_address = previous_peer
                    if peer_address not in peer_wrong_chain:
                        peer_wrong_chain.append(peer_address)
                    
            except:
                if peer_address not in peer_blacklist:
                    peer_blacklist.append(peer_address)
                if previous_peer:
                    peer_address = previous_peer
                    peer_status = json.loads(os.popen('curl -m 2 -s {}:8888/status'.format(peer_address)).read())

            peer_height = peer_status['last_added_block_info']['height']
        except:
            peer_height = 'null'
    else:
        peer_height = 'null'


    index = 1
    #mgr block_info.addstr(index, 2, 'Local height : ', curses.color_pair(1))
    #mgr block_info.addstr('{}'.format(local_height), curses.color_pair(4))
    dataJson['casper_block_info']['Local height']=local_height

    index += 1
    #mgr block_info.addstr(index, 2, 'Peer height  : ', curses.color_pair(1))
    #mgr block_info.addstr('{}'.format(peer_height), curses.color_pair(4))
    dataJson['casper_block_info']['Peer height']=peer_height

    #mgr  block_info.addstr(index,34,'<- {} Peer : '.format('   From' if peer_address not in trusted_ips else 'Trusted'), curses.color_pair(1))
    #mgr block_info.addstr('{}'.format(peer_address), curses.color_pair(4 if peer_address not in trusted_ips else 5))
    

    index += 1
    #mgr block_info.addstr(index, 2, 'Round Length : ', curses.color_pair(1))
    #mgr block_info.addstr('{}'.format(round_length), curses.color_pair(4))
    dataJson['casper_block_info']['Round Length']=round_length

    bar_length = 34
    global round_time
    global avg_rnd_time

    if not has_been_active:
        round_time = datetime.utcnow()
    elapsed = datetime.utcnow() - round_time
    number_seconds = elapsed.total_seconds()
    round_percent = (number_seconds/avg_rnd_time)*100
    minutes = int(number_seconds/60)
    seconds = int(number_seconds%60)
    milliseconds = int(float(number_seconds - int(number_seconds)) * 1000)
    round_string = '{:01d}m {:02d}s {:03d}ms'.format(minutes, seconds, milliseconds)
    string_start_x = ((bar_length-len(round_string))/2) + 34
    
    if  round_percent > 99:
         round_percent= 100

    #mgr for x in range(bar_length):
    #mgr     block_info.addstr(index,34+x,' ', curses.color_pair(6))

    num_blocks = int(float(round_percent/(100/bar_length)))
    #mgr for x in range(num_blocks):
    #mgr     block_info.addstr(index,34+x,' ', curses.color_pair(16))

    #mgr block_info.move(index,int(string_start_x))
    char_index = 0
    #mgr for each_char in round_string:
    #mgr     block_info.addstr(each_char, curses.color_pair(7 if string_start_x+char_index < 34 + num_blocks else 3))
    #mgr     char_index += 1
    dataJson['casper_block_info']['Elapsed']=round_string
    dataJson['casper_block_info']['Round Percentage']=round_percent
    index += 1
    #mgr block_info.addstr(index, 2, 'Next Upgrade : ', curses.color_pair(1))
    #mgr block_info.addstr('{}'.format(next_upgrade), curses.color_pair(4 if next_upgrade == None else 5))
    dataJson['casper_block_info']['Next Upgrade']=format(next_upgrade)

    avg_num_blocks = 110
    block_percent = 1
    number_blocks = 0

    if local_era in era_block_start and  local_era-1 in era_block_start:
        number_blocks = era_block_start[local_era]-era_block_start[local_era-1]
        block_percent = int((era_block_start[local_era]-era_block_start[local_era-1])/avg_num_blocks*100)

    if next_upgrade:
        elapsed = datetime.utcnow() - round_time
        eras_left = next_era_upgrade - local_era - 1
        block_left = avg_num_blocks - number_blocks
        number_seconds = int(eras_left * (2*60*60) + (block_left * avg_rnd_time) + (avg_rnd_time - elapsed.total_seconds()))

        if number_seconds < 1:
            number_seconds = 0

        day = number_seconds // (24 * 3600)
        time = number_seconds % (24 * 3600)
        hour = time // 3600
        time %= 3600
        minutes = time // 60
        time %= 60
        seconds = time

        if day:
            round_string = 'Era {} in ~{}d {}h {:02d}m {:02d}s'.format(next_era_upgrade, day, hour, minutes, seconds)
        elif hour:
            round_string = 'Era {} in ~{}h {:02d}m {:02d}s'.format(next_era_upgrade, hour, minutes, seconds)
        elif minutes:
            round_string = 'Era {} in ~{}m {:02d}s'.format(next_era_upgrade, minutes, seconds)
        else:
            round_string = 'Era {} in ~{}s'.format(next_era_upgrade, seconds)

        string_start_x = ((bar_length-len(round_string))/2) + 34

        #mgr for x in range(bar_length):
        #mgr     block_info.addstr(index,34+x,' ', curses.color_pair(18))

        #mgr block_info.addstr(index,int(string_start_x), round_string, curses.color_pair(18))

    index += 1
    #mgr block_info.addstr(index, 2, 'Build Version: ', curses.color_pair(1))
    #mgr block_info.addstr('{}'.format(build_version), curses.color_pair(4))
    dataJson['casper_block_info']['Build Version']=format(build_version)

    index += 1
    #mgr block_info.addstr(index, 2, 'Proposer     : ', curses.color_pair(1))
    #mgr block_info.addstr('{}...{}'.format(current_proposer[:24],current_proposer[-24:]), curses.color_pair(4 if current_proposer != public_key else 5))
    dataJson['casper_block_info']['Proposer']='{}...{}'.format(current_proposer[:24],current_proposer[-24:])

    index += 2
    #mgr block_info.addstr(index, 2, 'Chain Name   : ', curses.color_pair(1))
    #mgr block_info.addstr('{}'.format(chain_name), curses.color_pair(4))
    dataJson['casper_block_info']['Chain Name']=format(chain_name)

    #mgr block_info.addstr(index, 34, 'Starting Hash : ', curses.color_pair(1))
    #mgr block_info.addstr('{}'.format(root_hash), curses.color_pair(4))
    dataJson['casper_block_info']['Starting Hash']=format(root_hash)

    index += 1
    #mgr block_info.addstr(index, 2, 'API Version  : ', curses.color_pair(1))
    #mgr block_info.addstr('{}'.format(api_version), curses.color_pair(4))
    dataJson['casper_block_info']['API Version']=format(api_version)

    index += 1
    #mgr block_info.addstr(index, 2, 'Local ERA    : ', curses.color_pair(1))
    #mgr block_info.addstr('{}'.format(local_era), curses.color_pair(4))
    dataJson['casper_block_info']['Local ERA']=format(local_era)

    if block_percent > 99:
        block_percent = 100

    #mgr for x in range(bar_length):
    #mgr     block_info.addstr(index,34+x,' ', curses.color_pair(6))

    num_blocks = int(float(block_percent/(100/bar_length)))
    #mgr for x in range(num_blocks):
    #mgr     block_info.addstr(index,34+x,' ', curses.color_pair(16))

    blocks_string = 'Processing Block: {}'.format(number_blocks)
    string_start_x = ((bar_length-len(blocks_string))/2) + 34
    #mgr block_info.move(index,int(string_start_x))
    char_index = 0
    #mgr for each_char in blocks_string:
    #mgr     block_info.addstr(each_char, curses.color_pair(7 if string_start_x+char_index < 34 + num_blocks else 3))
    #mgr     char_index += 1

    dataJson['casper_block_info']['Processing Block']=format(number_blocks)

    index += 2
    #mgr block_info.addstr(index, 2, 'Config File  : ', curses.color_pair(1))
    #mgr block_info.addstr('{}'.format(config_file), curses.color_pair(4))
    dataJson['casper_block_info']['Config File']=format(config_file)

    index += 1
    #mgr block_info.addstr(index, 2, 'Storage Path : ', curses.color_pair(1))
    #mgr block_info.addstr('{}'.format(node_path), curses.color_pair(4))
    dataJson['casper_block_info']['Storage Path']=format(node_path)

def casper_public_key():
    dataJson['casper_public_key'] = {}
    global pub_key_win
    global current_era_global
    global current_proposer

    #mgr pub_key_win = curses.newwin(4, 70, 22, 0)
    #mgr pub_key_win.box()
    #mgr box_height, box_width = pub_key_win.getmaxyx()
    #mgr text_width = box_width - 17 # length of the Text before it gets printed

    #mgr pub_key_win.addstr(0, 2, 'Public Key', curses.color_pair(4))
    #mgr pub_key_win.addstr(1, 2, '{}'.format(public_key), curses.color_pair(5))
    #mgr pub_key_win.addstr(2, 2, 'Balance      : ', curses.color_pair(1))
    dataJson['casper_public_key']['Public Key'] = '{}'.format(public_key)
    
    try:
        block_info = json.loads(os.popen('casper-client get-block').read())
        header_info = block_info['result']['block']['header']
        body_info = block_info['result']['block']['body']
        lfb_root = header_info['state_root_hash']
        currentBlock = int(header_info['height'])
        current_era_global = int(header_info['era_id'])
        era_block_start[current_era_global] = currentBlock
        current_proposer = body_info['proposer'].strip("\"")


        deploys = body_info['deploy_hashes']
        ProcessDeploy(deploys, currentBlock)

        transfers = body_info['transfer_hashes']
        if transfers:
            transfer = json.loads(os.popen('casper-client get-block-transfers -b {}'.format(currentBlock)).read())
            transfers = transfer['result']['transfers']
            block_hash = transfer['result']['block_hash'].strip("\"")
            root_hash = block_info['result']['block']['header']['state_root_hash']
            for transfer in transfers:
                print(transfer)
                amount = transfer['amount']
                source = transfer['source'].strip("\"")
                target = transfer['target'].strip("\"")
                transfer_dict['{}-{}-{}-{}'.format(currentBlock,block_hash,source,target)] = [currentBlock,amount,source,target,header_info['timestamp']]

        global purse_uref   # we only need to get this ref the first time
        if purse_uref == 0:
            query_state = json.loads(os.popen('casper-client query-state -k "{}" -s "{}"'.format(public_key, lfb_root)).read())
            purse_uref = query_state['result']['stored_value']['Account']['main_purse']

        balance_json = json.loads(os.popen('casper-client get-balance --purse-uref "{}" --state-root-hash "{}"'.format(purse_uref, lfb_root)).read())
        balance = int(balance_json['result']['balance_value'].strip("\""))

        if (balance > 100000000):
            #mgr pub_key_win.addstr('{:,.9f} CSPR'.format(balance / 1000000000), curses.color_pair(4))
            dataJson['casper_public_key']['Balance'] = '{:,.9f} CSPR'.format(balance / 1000000000)
        else:
            #mgr pub_key_win.addstr('{:,} mote'.format(balance), curses.color_pair(4))
            dataJson['casper_public_key']['Balance'] = '{:,} mote'.format(balance)

        coin_len = len(current_price)
        #mgr pub_key_win.addstr(2, 70-coin_len-8-7-4, 'Price: ', curses.color_pair(1))
        #mgr pub_key_win.addstr('${} CSPR-USD'.format(current_price), curses.color_pair(4))
        dataJson['casper_public_key']['Price'] = '${} CSPR-USD'.format(current_price)

    except:
        current_era_global = 0
        #mgr pub_key_win.addstr('Not available yet', curses.color_pair(2))
        dataJson['casper_public_key']['Balance'] = '0'


def casper_validator():
    global validator
    dataJson['casper_validator'] = {}
    #mgr validator = curses.newwin(8, 70, 26, 0)
    #mgr validator.box()
    #mgr box_height, box_width = validator.getmaxyx()
    #mgr text_width = box_width - 17 # length of the Text before it gets printed
    #mgr validator.addstr(0, 2, 'Casper Validator Info', curses.color_pair(4))

    local_era = 0
    try:
        last_added_block_info = local_status['last_added_block_info']

        try:
            local_era = last_added_block_info['era_id']
        except:
            local_era = 0
    except:
        local_era = 0

    current_era = future_era = 0
    current_weight = future_weight = 0
    num_cur_validators = num_fut_validators = 0
    current_index = future_index = 0

    try:
        global auction_info
        global current_weights
        current_weights = dict()
        future = dict()

        auction_info = json.loads(os.popen('casper-client get-auction-info').read())
        auction_info = auction_info['result']['auction_state']
        bid_info = auction_info['bids']
    
        current_validators = auction_info['era_validators'][0]['validator_weights']
        current_era = auction_info['era_validators'][0]['era_id']
        for item in current_validators:
            key = item['public_key'].strip("\"");
            value = int(item['weight'].strip("\""))
            current_weights[key] = value
            if key == public_key:
                current_weight = value

        missing_validators.clear()
        if event_ptr.has_finality():
            for key in current_weights.keys():
                if key not in finality_signatures:
                    missing_validators.append(key)

        future_validators = auction_info['era_validators'][1]['validator_weights']
        future_era = auction_info['era_validators'][1]['era_id']
        for item in future_validators:
            key = item['public_key'].strip("\"");
            value = int(item['weight'].strip("\""))
            future[key] = value
            if key == public_key:
                future_weight = value

        #arg... indexing a sorted is not working... so I'll just iterate for now...
        index = 1
        for item in sorted(current_weights.items(), key=lambda x: x[1], reverse=True):
            if item[0] == public_key:
                current_index = index
                break
            index += 1

        index = 1
        for item in sorted(future.items(), key=lambda x: x[1], reverse=True):
            if item[0] == public_key:
                future_index = index
                break
            index += 1

        num_cur_validators = len(current_validators)
        num_fut_validators = len(current_validators)

    except:
        current_weight = 0
        future_weight = 0
        current_validators = 0
        current_era = 0
        bid_info = []
        pass

    #mgr validator.addstr(1, 2, 'Validators   : ', curses.color_pair(1))
    #mgr validator.addstr('{:,} / {:,} / {:,} / {}'.format(num_cur_validators, num_fut_validators, len(bid_info), validator_slots), curses.color_pair(4))
    #mgr validator.addstr(1, 42, '<- {}/{}/Bids/Slots'.format(current_era, future_era), curses.color_pair(1))
    dataJson['casper_validator']['Validators'] = '{:,} / {:,} / {:,} / {} '.format(num_cur_validators, num_fut_validators, len(bid_info), validator_slots)
    # get the length of the printed string so we can right justify and not leave blank spaces
    if current_weight > 10000000000:
        current_str = '{:,.4f} CSPR'.format(current_weight/1000000000)
    else:
        current_str = '{:,.9f} CSPR'.format(current_weight/1000000000)

    if future_weight > 10000000000:
        future_str = '{:,.4f} CSPR'.format(future_weight/1000000000)
    else:
        future_str = '{:,.9f} CSPR'.format(future_weight/1000000000)

    longest_len = max(len(current_str), len(future_str))

    global money_string_length
    money_string_length = longest_len

    #mgr validator.addstr(2, 2, 'ERA {} : '.format(str(current_era).ljust(8, ' ')), curses.color_pair(1))
    #mgr validator.addstr('{}'.format(current_str.rjust(longest_len, ' ')), curses.color_pair(4))
    #mgr validator.addstr(2, 42, '<- Position {}'.format(current_index), curses.color_pair(1))
    dataJson['casper_validator']['ERA {} : '.format(str(current_era).ljust(8, ' '))] ='{} <- Position {}'.format(current_str.rjust(longest_len, ' '),current_index)

    #mgr validator.addstr(3, 2, 'ERA {} : '.format(str(future_era).ljust(8, ' ')), curses.color_pair(1))
    #mgr validator.addstr('{}'.format(future_str.rjust(longest_len, ' ')), curses.color_pair(4))
    #mgr validator.addstr(3, 42, '<- Position {}'.format(future_index), curses.color_pair(1))
    dataJson['casper_validator']['ERA {} : '.format(str(future_era).ljust(8, ' '))]='{} <- Position {}'.format(future_str.rjust(longest_len, ' '),future_index)

    #mgr validator.addstr(4, 2, 'Last Reward  : ', curses.color_pair(1))
    reward = float(future_weight - current_weight)
    if (reward > 10000000):
        this_str = '{:,.4f} CSPR'.format(reward / 1000000000)
    else:
        this_str = '{:,} mote'.format(int(reward))
    #mgr validator.addstr('{}'.format(this_str.rjust(longest_len, ' ')), curses.color_pair(4))
    

    #mgr if current_weight:
        #mgr validator.addstr(4, 42, '<- {:.2%} yearly'.format((reward/current_weight)*12*365, 's' if len(our_rewards)>1 else ''), curses.color_pair(1))
    dataJson['casper_validator']['Last Reward']='{} <- {:.2%} yearly '.format(this_str.rjust(longest_len, ' '),(reward/current_weight)*12*365, 's' if len(our_rewards)>1 else '')
    #mgr validator.addstr(5, 2, 'Avg Reward   : ', curses.color_pair(1))
    reward = 0
    if len(our_rewards):
        reward = float(sum(our_rewards) / len(our_rewards))
    if reward > 10000000:
        this_str = '{:,.4f} CSPR'.format(reward / 1000000000)
    else:
        this_str = '{:,} mote'.format(int(reward))
    #mgr validator.addstr('{}'.format(this_str.rjust(longest_len, ' ')), curses.color_pair(4))
    

    if current_weight:
        #mgr validator.addstr(5, 42, '<- Last {} reward{} ({:.2%})'.format(len(our_rewards), 's' if len(our_rewards)>1 else '',((reward/current_weight) if current_weight else 0)*12*365), curses.color_pair(1))
        dataJson['casper_validator']['Avg Reward']='{} <- Last {} reward{} ({:.2%})'.format(this_str.rjust(longest_len, ' '),len(our_rewards), 's' if len(our_rewards)>1 else '',((reward/current_weight) if current_weight else 0)*12*365)
    else:
        #mgr validator.addstr(5, 42, '<- Last {} reward{}'.format(len(our_rewards), 's' if len(our_rewards)>1 else ''), curses.color_pair(1))
        dataJson['casper_validator']['Avg Reward']='{} <- Last {} reward{}'.format(this_str.rjust(longest_len, ' '),len(our_rewards), 's' if len(our_rewards)>1 else '')

    #mgr validator.addstr(6, 2, 'Blks Propsed : ', curses.color_pair(1))
    this_block = 0
    last_block = 0
    prev_block = 0
    avg_blocks = 0
    if current_era_global in our_blocks:
        this_block = our_blocks[current_era_global]
    if current_era_global-1 in our_blocks:
        last_block= our_blocks[current_era_global-1]
    if current_era_global-2 in our_blocks:
        prev_block = our_blocks[current_era_global-2]
    for era in our_blocks:
        avg_blocks += our_blocks[era]
    if len(our_blocks):
        avg_blocks /= len(our_blocks)

    #mgr validator.addstr('{}'.format(this_block), curses.color_pair(2 if this_block < int(avg_blocks) else 5 if this_block > int(avg_blocks) else 4))
    #mgr validator.addstr(' / ', curses.color_pair(4))
    #mgr validator.addstr('{}'.format(last_block), curses.color_pair(2 if last_block < int(avg_blocks) else 5 if last_block > int(avg_blocks) else 4))
    #mgr validator.addstr(' / ', curses.color_pair(4))
    #mgr validator.addstr('{}'.format(prev_block), curses.color_pair(2 if prev_block < int(avg_blocks) else 5 if prev_block > int(avg_blocks) else 4))
    #mgr validator.addstr(' / ', curses.color_pair(4))
    #mgr validator.addstr('{:.2f}'.format(avg_blocks), curses.color_pair(4))

    #mgr validator.addstr(6, 42, '<- {}/{}/{}/Avg'.format(current_era_global,current_era_global-1,current_era_global-2), curses.color_pair(1))


def draw_menu():
    k = 0
    cursor_x = 0
    cursor_y = 0

    # Clear and refresh the screen for a blank canvas
    #mgr casper.clear()
    #mgr casper.refresh()

    #mgr global main_window
    #mgr main_window = casper

    # Start colors in curses
    #mgr curses.start_color()
    #mgr curses.init_pair( 1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    #mgr curses.init_pair( 2, curses.COLOR_RED, curses.COLOR_BLACK)
    #mgr curses.init_pair( 3, curses.COLOR_BLACK, curses.COLOR_WHITE)
    #mgr curses.init_pair( 4, curses.COLOR_GREEN, curses.COLOR_BLACK)
    #mgr curses.init_pair( 5, curses.COLOR_YELLOW, curses.COLOR_BLACK)

    #mgr curses.init_pair( 6, curses.COLOR_GREEN, curses.COLOR_WHITE)
    #mgr curses.init_pair( 7, curses.COLOR_BLACK, curses.COLOR_GREEN)
    #mgr curses.init_pair( 8, curses.COLOR_BLACK, curses.COLOR_CYAN)
    #mgr curses.init_pair( 9, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    #mgr curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_RED)

    #mgr curses.init_pair(11, curses.COLOR_BLACK, curses.COLOR_MAGENTA)
    #mgr curses.init_pair(12, curses.COLOR_BLACK, curses.COLOR_CYAN)
    #mgr curses.init_pair(13, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    #mgr curses.init_pair(14, curses.COLOR_BLACK, curses.COLOR_RED)
    #mgr curses.init_pair(15, curses.COLOR_BLACK, curses.COLOR_WHITE)

    #mgr curses.init_pair(16, curses.COLOR_BLACK, curses.COLOR_GREEN)
    #mgr curses.init_pair(17, curses.COLOR_GREEN, curses.COLOR_RED)
    #mgr curses.init_pair(18, curses.COLOR_YELLOW, curses.COLOR_RED)

    #mgr curses.init_pair(18, curses.COLOR_BLACK, curses.COLOR_CYAN)

    #mgr curses.init_pair(20, curses.COLOR_RED, curses.COLOR_WHITE)

    global blink
    blink = False
    
    config.read('/etc/casper/1_0_0/chainspec.toml')
    global validator_slots
    validator_slots = config.get('core', 'validator_slots').strip('\'')

    global cpu_cores
    cpu_cores = os.cpu_count()

    global cpu_name
    cpu_name = get_processor_name()

    global has_been_active
    has_been_active = False

    # Loop where k is the last character pressed
    while (k != ord('q')):

        # Initialization
        #mgr casper.erase()
        #mgr casper.noutrefresh()
        #mgr global main_height
        #mgr global main_width
        #mgr main_height, main_width = casper.getmaxyx()

        blink = blink ^ True

        #mgr cursor_x = main_width-1
        #mgr cursor_y = main_height-1

        casper_launcher()
        casper_block_info()
        casper_public_key()
        casper_validator()
        casper_peers()
        system_memory()
        system_disk()
        system_cpu()
        casper_bonds()
        casper_era_rewards()
        casper_proposers()
        casper_events()
        casper_transfers()
        casper_deploys()

        # Render status bar
        statusbarstr = "Press 'ctrl-c' to exit | STATUS BAR "
        #mgr casper.attron(curses.color_pair(3))
        #mgr casper.addstr(main_height-1, 1, statusbarstr)
        #mgr casper.addstr(main_height-1, len(statusbarstr), " " * (main_width - len(statusbarstr) - 1))
        #mgr casper.attroff(curses.color_pair(3))

        # Refresh the screen

        #mgr launcher.noutrefresh()
        #mgr block_info.noutrefresh()
        #mgr pub_key_win.noutrefresh()
        #mgr validator.noutrefresh()
        #mgr sysmemory.noutrefresh()
        #mgr peers.noutrefresh()
        #mgr sysdisk.noutrefresh()
        #mgr syscpu.noutrefresh()
        #mgr bonds.noutrefresh()
        #mgr era_rewards.noutrefresh()
        #mgr proposers.noutrefresh()
        #mgr events.noutrefresh()
        #mgr transfers_view.noutrefresh()
        #mgr deploy_view.noutrefresh()

        #mgr casper.noutrefresh()
        #mgr curses.doupdate()
        dataJson['last_update']= datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        with open(JSON_FILE, 'w') as outfile:
            json.dump(dataJson, outfile)
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            event_ptr.terminate()
            break;

        #mgr if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        #mgr     k = casper.getch()

def main():
    os.environ['NCURSES_NO_UTF8_ACS'] = '1'

    
    global config
    config = ConfigParser()

    global node_path
    global config_file
    config_file = '/etc/casper/1_0_0/config.toml'

    try:
        subfolders = [ f.path for f in os.scandir('/etc/casper/') if f.is_dir() and re.match(r'\d{0,255}_\d{0,255}_\d{0,255}', f.name) ]
        for folder in sorted(subfolders, reverse=True):
            config_file = '{}/config.toml'.format(folder)
            break;
    except:
        pass

    config.read(config_file)
    node_path = config.get('storage', 'path').strip('\'')

    global trusted_ips
    global testing_trusted
    testing_trusted = True

    trusted_ips = []
    known = config.get('network', 'known_addresses').strip('[]').split(',')
    for ip in known:
        clean_ip = ip.strip('\'') if ':' not in ip else ip.strip('\'').split(':')[0]
        if clean_ip not in trusted_ips:
            trusted_ips.append(clean_ip)

    global random
    random = random.SystemRandom()

    global localhost
    localhost = 'localhost'

    global round_time
    round_time = datetime.utcnow()
    global avg_rnd_time
    avg_rnd_time = 65.536

    global current_proposer
    current_proposer = ''

    global public_key
    public_key = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'k:h:')
        for opt, arg in opts:
            if opt == '-k':
                public_key = arg
            elif opt == '-h':
                localhost = str(arg)
    except:
        pass

    if not public_key:
        try:
            local_status = json.loads(os.popen('curl -s {}:8888/status'.format(localhost)).read())
            public_key = local_status['our_public_signing_key']
        except:
            reader = open('/etc/casper/validator_keys/public_key_hex')
            try:
                public_key= reader.read().strip()
            finally:
                reader.close()

    global last_val_reward
    global last_del_reward

    last_val_reward = 0
    last_del_reward = 0

    global thread_ptr
    global event_ptr
    event_ptr = EventTask()
    thread_ptr = threading.Thread(target=event_ptr.run)
    thread_ptr.daemon = True
    thread_ptr.start()

    global proposer_thread_ptr
    global proposer_ptr
    proposer_ptr = ProposerTask()
    proposer_thread_ptr = threading.Thread(target=proposer_ptr.run)
    proposer_thread_ptr.daemon = True
    proposer_thread_ptr.start()

    global era_thread_ptr
    global era_ptr
    era_ptr = EraTask()
    era_thread_ptr = threading.Thread(target=era_ptr.run)
    era_thread_ptr.daemon = True
    era_thread_ptr.start()

    global cpu_thread_ptr
    global cpu_ptr
    cpu_ptr = CpuTask(86400)
    cpu_thread_ptr = threading.Thread(target=cpu_ptr.run)
    cpu_thread_ptr.daemon = True
    cpu_thread_ptr.start()

    global peers_thread_ptr
    global peers_ptr
    peers_ptr = PeersTask()
    peers_thread_ptr = threading.Thread(target=peers_ptr.run)
    peers_thread_ptr.daemon = True
    peers_thread_ptr.start()

    global current_price
    current_price = "0"

    global coinlist_thread_ptr
    global coin_ptr
    coin_ptr = CoinListTask()
    coin_thread_ptr = threading.Thread(target=coin_ptr.run)
    coin_thread_ptr.daemon = True
    coin_thread_ptr.start()

    global scan_validators_thread_ptr
    global scan_validators_ptr
    scan_validators_ptr = ScanValidatorsTask()
    scan_validators_thread_ptr = threading.Thread(target=scan_validators_ptr.run)
    scan_validators_thread_ptr.daemon = True
    scan_validators_thread_ptr.start()
    #server = HTTPServer(('', PORT), MyServer)
    #server.serve_forever()
    WebThread().start()
    draw_menu()

    #mgr curses.wrapper(draw_menu)

if __name__ == "__main__":
    main()
