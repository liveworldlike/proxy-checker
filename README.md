# Description

Simple multi-threading proxy checker.

Takes several files with proxies, 1 proxy/line as input, tries to connect to "http(s)://google.com" through proxy using http, https and socks5 protocols, and print results.

# Requirements

+ Python 3.4  
+ [requests](https://github.com/requests/requests)
+ [pySocks](https://github.com/Anorov/PySocks)

# Usage

                      proxy-checker <-f file with proxies [-f file2, -f file3...]> [options] 
                  
