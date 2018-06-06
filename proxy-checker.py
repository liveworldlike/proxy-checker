import threading, requests, sys, socks
from queue import *
from functools import reduce
from colorama import *

################################################################################
#                                 Сообщения                                    #
################################################################################
################################################################################

# Справка

help = """Простой многопоточный прокси-чекер.
Принимает файл с прокси в формате хост(или ip):порт, один прокси на линию.
Использование: {0} <-f файл с прокси [-f файл2, -f файл3...]> [другие опции]
Общее:
        -h      --help                  показать эту справку и выйти
        
Вывод:
        -a      --show-all              показывать и рабочие и нерабочие прокси

        -g      --show-good             показывать только рабочие прокси
                                        (по умолчанию)

        -b      --show-bad              показывать только нерабоие прокси
        
                --format                печетать и записывать прокси в файл в цвете и в формате 
                                        хост:порт +/-(http) +/-(https) +/-(socks5)
                                        (по умолчанию)
                
                --no-format             печатать прокси в формате хост:порт, и не раскрашивать их

        -q      --quiet                 не показывать ошибки
        
        
Файловый ввод/вывод:
        -o      --out                   назначить файл для вывода прокси
                                        (по умолчанию - /dev/null)

        -f      --file                  указать файл с прокси

Потоки:
        -c      --threads-count         указать количество потоков
                                        (по умолчанию - 10)

Проверка: 
                
                --timeout               Указать время таймаута (в секундах)
                                        (по умолчанию - 0.5)
        
                --http-url              ссылка для проверки http прокси
                                        (для этой опции и остальных похожих url должен указываться вместе со схемой)
                                        (по умолчанию - http://google.com)
        
                --https-url            ссылка для проверки https прокси
                                       (по умолчанию- https://google.com)
                
                --socks5-url           ссылка для проверки socks5 прокси 
                                        (по умолчанию - http://google.com)""".format(sys.argv[0])

usage = """Использование: {0} <-f файл с прокси> [другие опции]
Попробуйте --help, чтобы узнать больше.""".format(sys.argv[0])

################################################################################



################################################################################
#                                 Функции                                      #
################################################################################
################################################################################

def error(mode, error):       # Функция, которая показывает ошибки. 
    if not mode: print(error) # Выведет сообщение, только если mode равен False
    
def arguments_parser():       # Функция, которая разбирает аргументы командной строки
    if len(sys.argv) < 2:     
        print(usage)
        sys.exit(1)
        
    args = sys.argv[1:] # Обрезаем имя исполняемого файла
    
    proxies = [] # Массив с прокси, которые будут получены
    result = {   # Словарь с информацией, полученной из аргументов командной строки  
        'show'          : 'good',               # Тип показываемых прокси. Принимает значения: good|bad|all
        'threads_count' : 10,                   # Количество потоков
        'out_file'      : '/dev/null',          # Выходной файл
        'urls'          : {                     # URL для проверки прокси, по одному на протокол. 
            'http'         : 'http://google.com',
            'https'        : 'https://google.com',
            'socks5'       : 'http://google.com'
                          },  
        'protocols'     : ['http', 'https', 'socks5'], # Протоколы, с помощью которых скрипт будет пытаться соединиться с прокси
        'accept'        : ['http', 'https', 'socks5'], # Будут показаны только прокси, поддерживающие хотя бы один из этих протоколов 
        'timeout'       : 0.5, # Количество времени (в секундах) до сброса соединения
        
        'format'        : True,                 # Строки будут показываться в цвете
        'quiet'         : False                 # Если True, ошибки не будут показываться 
    }    
    
    # Сначала проверяем наличие ключей с высоким приоритетом
    if '-h' in args or '--help' in args:     # Если кто-то зовет на помощь, всё остальное может подождать!
        print(help)                          # Выводим справку
        sys.exit(0)                          # И завершаем программу.
  
    if '-q' in args or '--quiet' in args:    # Если нас попросили вести себя потише
        result['quiet'] = True               # Записываем это
    
    # Основное тело функции все аргументы проходятся в цикле  

    for i in range(len(args)): # Используем индекс элемента вместо, собственно, элемента, 
                               # потому что так легче получить следующий аргумент
           
        if args[i] in ['-f', '--file']:      
            file_name = args[i + 1]  
            try:                    # Пробуем открыть и прочитать файл
                file = open(file_name)
                proxies += [proxy.strip() for proxy in file] 
                                   # += вместо = используется для возможности использования сразу нескольких файлов
                                   # .strip() - обрезаем \n в конце строки 
                file.close()
            except:             # Если не получилось открыть файл, выводим сообщение об ошибке
                error(result['quiet'], 'Не удалось открыть %s.' % file_name)
            
            
        elif args[i] in ['-c', '--threads-count']:
            try:                # Пробуем преобразовать строку в число
                result['threads_count'] = int(args[i + 1])
            except ValueError:  # Если строка неправильная, выводим сообщение об ошибке
                error(result['quiet'],
                      'Не удалось задать количество потоков: не удалось распознать число: %s.'
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
            try:                # Пробуем преобразовать строку в число 
                result['timeout'] = float(args[i + 1])
            except ValueError:  # Если строка неправильная, выводим сообщение об ошибке
                error(result['quiet'], 
                      'Не удалось задать время таймаута: не удалось распознать число: %s.' 
                       % args[i + 1])          
        
        # Параметры показа:
        
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

    if proxies == []: # Если нет прокси на проверку, завершаем программу с кодом 1      
        error(result['quiet'], 'Прокси на проверку не найдены.')
        sys.exit(1)
        
    return proxies, result

def main():
    proxies, data = arguments_parser() # Получаем массив с прокси и словарь с параметрами
    threads = []                       # Создаем пока что пустой массив для потоков
    queue = Queue()                    # Создаём очередь с прокси
    file_locker = threading.Lock()     # Создаём блокировщик консольного и файлового выводов
    if data['format']:                 # Если вывод должен быть отформатирован, печатаем заголовок таблицы
        print('%22s\thttp\thttps\tsocks5' % 'hostname/ip')
    for proxy in proxies: 
        queue.put(proxy)               # Заполняем очередь прокси
    for i in range(data['threads_count']):         # Создаём потоки
        thread = Checker(data, queue, file_locker) # Создаём один поток 
        threads.append(thread)                     # Добавляем его к массиву
        thread.start()                             # И запускаем его
    for thread in threads: 
        thread.join()      # Ждём пока все потоки не завершатся     
################################################################################



################################################################################
#                                    Классы                                    #
################################################################################

class Checker(threading.Thread): # Класс потока
    def __init__(self, data, queue, file_locker):
        self.data = data                # Словарь с параметрами
        self.queue = queue              # Очередь
        self.locker = file_locker
        threading.Thread.__init__(self) 
        
    def run(self): # Основная функция класса
        
        gen_proxies = lambda protocol, proxy: { # Функция, генерирующая словарь с прокси
            'http'  : protocol + '://' + proxy,
            'https' : protocol + '://' + proxy
            }
        
        while not self.queue.empty():  # Пока очередь не пуста
            proxy = self.queue.get() # Получаем из очереди прокси, который нужно проверить
            valid = {}.fromkeys(self.data['protocols'], False) # Создаем словарь, показывающий, прошёл ли прокси проверку для определённого протокола, или нет.
            for protocol in self.data['protocols']: # Последовательно проходим по всем заданным протоколам.
                try: # Пробуем подключиться к указанному url через прокси
                    valid[protocol] = requests.get(
                        self.data['urls'][protocol],
                        proxies = gen_proxies(protocol, proxy),
                        timeout = self.data['timeout']
                    ).ok # Если запрос завершился удачно, то прокси работает
                except requests.exceptions.ReadTimeout: # Если просто истекло время, даём ещё один шанс
                    try:
                        valid[protocol] = requests.get(
                            self.data['urls'][protocol],
                            proxies = gen_proxies(protocol, proxy)
                        ).ok
                    except: valid[protocol] = False # Если возникли ошибки, 
                except: valid[protocol] = False # прокси нерабочий
            if self.data['format']: # Если нужно отформатировать вывод, то форматируем его.
                proxy = '%22s\t%s\t%s\t%s' % ( 
                                               proxy,
                    '+' if valid['http']   else '-',
                    '+' if valid['https']  else '-',
                    '+' if valid['socks5'] else '-'
                )
            is_valid = reduce( # Переменная верна, если прокси работает хотя бы по одному из указанных протоколов
                lambda a, b: a or b, 
                [valid[key] for key in self.data['accept']]
                ) 
            if is_valid and self.data['show'] != 'bad' or self.data['show'] != 'good':
                # Если прокси работает, и нерабочие прокси не показываются
                # или если прокси не работает, и рабочие прокси не показываются
                with self.locker: # Блокируем вывод
                    if self.data['format']:
                        if is_valid: # Раскрашиваем вывод, если нужно его отформатировать
                            proxy = Fore.GREEN + proxy + Fore.RESET # Если прокси работает, то в зелёный
                        else:
                            proxy = Fore.RED + proxy + Fore.RESET   # А если нет, то в красный               
                    print(proxy)  # Выводим прокси на экран
                    try:          # Пробуем открыть файл и записать прокси.
                        file = open(self.data['out_file'], 'a')
                        file.write(proxy + '\n')
                        file.close()
                    except:       # Если возникла ошибка, выводим сообщение
                        error(self.data['quiet'], 
                              'Не удалось открыть %s.' % self.data['out_file'])
                        
if __name__ == '__main__': main()
