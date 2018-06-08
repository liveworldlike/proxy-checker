#!/usr/bin/python3
import threading, requests, sys, socks
from queue import *
from functools import reduce
import colorama

help = """Simple multi-threading proxy checker.
Proxy format: host:port, 1 proxy/line
Usage: {0} <-f file with proxies> [-f file2 -f file3...] [keys]
Keys:
        -h      --help                  show this message and exit
Output:
        -a      --show-all              show good and bad proxies either
        -g      --show-good             show only good proxies
                                        (defaul option)
        -b      --show-bad              show only bad proxies
                --format                print and write proxies in format host:port +/- +/- +/-
                                        (default option)
                --no-format             print and write proxies without color: host:port
        -q      --quiet                 don't show errors
Files:
        -o      --out                   specify output file
                                        (default value - /dev/null)
        -f      --file                  specify input file
Threads:
        -c      --threads-count         set the number of threads
                                        (default value - 10)
Connecting: 
        -t      --tries                 set the number of tries
                                        (default value - 5)
                --timeout               set timeout in seconds
                                        (default value - 0.5)
                --http-url              host to check http proxies 
                                        (default value - http://google.com)
                --https-url            host to check https proxies 
                                        (default value - https://google.com)
                --socks5-url           host to check socks5 proxies 
                                        (default value - http://google.com)""".format(sys.argv[0])

usage = """Usage: {0} <-f file with proxies> [keys]
Try --help.""".format(sys.argv[0])


def error(mode, error):       
    if not mode: print(error) 
    
def arguments_parser():
    if len(sys.argv) < 2:
        print(usage)
        sys.exit(0)
        
    args = sys.argv[1:] 
    
    proxies = [] 
    result = {   
        'show'          : 'good',               # all | good | bad
        'threads_count' : 10,                 
        'out_file'      : '/dev/null',         
        'urls'         : {                   
            'http'         : 'http://google.com',
            'https'        : 'https://google.com',
            'socks5'       : 'http://google.com'
                          },  
        'protocols'     : ['http', 'https', 'socks5'], 
        'accept'        : ['http', 'https', 'socks5'], 
        'timeout'       : 0.5,
        
        'format'        : True,
        'quiet'         : False           
    }    
    
    # Check high-priority keys first:
    if '-h' in args or '--help' in args:
        print(help)                      
        sys.exit(0)               

    if '-q' in args or '--quiet' in args:
        result['quiet'] = True 
    
    # The main body of parser  
    for i in range(len(args)):         
        if args[i] in ['-f', '--file']:      
            file_name = args[i + 1] 
            try:                 
                file = open(file_name)
                proxies += [proxy.strip() for proxy in file] 
                file.close()
            except:         
                error(result['quiet'], 'Unable to open file %s.' % file_name)
            
            
        elif args[i] in ['-c', '--threads-count']:
            try:  
                result['threads_count'] = int(args[i + 1])
            except ValueError: 
                error(result['quiet'], 
                      'Can\'t set number of threads: %s is not a valid number.' 
                      % args[i + 1])

        elif args[i] in ['-o', '--out']: 
            result['out_file'] = args[i + 1]
        
        elif args[i] in ['--url-http']: 
            result['urls']['http'] = args[i + 1]
            
        elif args[i] in ['--url-https']: 
            result['urls']['https'] = args[i + 1]   
        
        elif args[i] in ['--url-socks5']: 
            result['urls']['socks5'] = args[i + 1] 
            
        elif args[i] in ['--timeout']:
            try:                
                result['timeout'] = float(args[i + 1])
            except ValueError:
                error(result['quiet'], 
                      'Can\'t set timeout: %s is not a valid number.' 
                       % args[i + 1])          
        
        # How to show:
        
        elif args[i] in ['-a', '--show-all']:
            result['show'] = 'all'
                    
        elif args[i] in ['-g', '--show-good']:
            result['show'] = 'good'
                    
        elif args[i] in ['-b', '--show-bad']:
            result['show'] = 'bad'
             
        elif args[i] in ['--no-format']:
            result['format'] = False    
            
        elif args[i] in ['--format']:
            result['format'] = True         

    if proxies == []:     
        error(result['quiet'], 'Proxy not found.')
        sys.exit(1)
        
    return proxies, result

def main():
    colorama.init()
    proxies, data = arguments_parser() 
    threads = []
    queue = Queue()
    file_locker = threading.Lock()
    if data['format']:
        print('%22s\thttp\thttps\tsocks5' % 'hostname/ip')
    for proxy in proxies: 
        queue.put(proxy)      
    for i in range(data['threads_count']):
        thread = Checker(data, queue, file_locker, i) 
        threads.append(thread)                     
        thread.start()                         
    for thread in threads: 
        thread.join()      

        
class Checker(threading.Thread):
    def __init__(self, data, queue, file_locker, ID):
        self.data = data               
        self.queue = queue             
        self.ID = ID
        self.locker = file_locker       
        threading.Thread.__init__(self) 
        
    def run(self):
        
        gen_proxies = lambda protocol, proxy: {
            'http'  : protocol + '://' + proxy,
            'https' : protocol + '://' + proxy
            }
        
        while not self.queue.empty():
            proxy = self.queue.get()
            valid = {}.fromkeys(self.data['protocols'], False) 
            for protocol in self.data['protocols']:
                try: 
                    valid[protocol] = requests.get(
                        self.data['urls'][protocol],
                        proxies = gen_proxies(protocol, proxy),
                        timeout = self.data['timeout']
                    ).ok 
                except requests.exceptions.ReadTimeout: 
                    try:
                        valid[protocol] = requests.get(
                            self.data['urls'][protocol],
                            proxies = gen_proxies(protocol, proxy),
                            timeout = 60
                        ).ok
                    except: 
                        valid[protocol] = False 
                except: 
                    valid[protocol] = False 
            if self.data['format']:
                proxy = '%22s\t%s\t%s\t%s' % ( 
                                               proxy,
                    '+' if valid['http']   else '-',
                    '+' if valid['https']  else '-',
                    '+' if valid['socks5'] else '-'
                )
                
            is_valid = reduce( # If proxy support any of this protocol
                lambda a, b: a or b, 
                [valid[key] for key in self.data['accept']]
                ) 
        
            if is_valid and self.data['show'] != 'bad' or self.data['show'] != 'good':
                with self.locker: 
                    if self.data['format']:
                        if is_valid:
                            print(colorama.Fore.GREEN + proxy + colorama.Fore.RESET)
                        else:
                            print(colorama.Fore.RED + proxy + colorama.Fore.RESET                    
                    try:
                        file = open(self.data['out_file'], 'a')
                        file.write(proxy + '\n')
                        file.close()
                    except:
                        error(self.data['quiet'], 
                              'Unable to open file %s.' % self.data['out_file'])
                        
if __name__ == '__main__': main()
