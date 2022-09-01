#!/usr/bin/env python3
from curses.panel import bottom_panel
from time import time, sleep
import logging
import argparse
import kioconfig
import kioprinter
import gpiolib
import bclib
import kiocurl
import sys,re,os

wdObj=None

def main():
    logging.basicConfig(format='%(asctime)s - %(message)s',filename='/home/pi/kiosk.log',filemode='w',level=logging.DEBUG)
    #logging.basicConfig(format='%(asctime)s - %(message)s',level=logging.DEBUG)
    global wdObj
    def make_URL(bar_code):
        '''
        Returns url for cURL request
        '''
        #Remove bc type prefix if present
        if not bar_code[0].isnumeric():
            bar_code=bar_code[1:]
        req_code = re.search(config['bc_regex'],bar_code)
        if req_code is not None:
            req_code = req_code.group(0)
            req_code=req_code.replace('#','%23')
            return(config['url'].format(config['host'],req_code,lang))
        return(None)

    def init_kiosk():
        '''
        Tests pheriferials for kiosk op
        '''
        ledsObj.on()
        buttonsObj.beep(background=False)
        #Init barcode reader, do not start kiosk while bcr not running
        bcrObj.start()
        ledsObj.pulse([2],fade_in_time=.1,fade_out_time=.1,n=None)
        while not bcrObj.running:
            sleep(5)
            bcrObj.next()
        logging.info('BC reader on {}'.format(config['bc_reader_port']))
        sleep(delay)
        #Indicate bc OK
        ledsObj.off([2])
        #Init printer, check if avilable, do not start kiosk while bcr not running
        ledsObj.pulse([1],fade_in_time=.1,fade_out_time=.1,n=None)
        prnObj.start()
        #Reset printsystem if reset button is pressed
        if (buttonsObj.pressed() and buttonsObj.pressedButtons == [1]):
                logging.info('User printsystem reset initiated')
                prnObj.deleteAllPrinters()
                prnObj.installKioPrinter()
                buttonsObj.beep(background=False,n=3)

        while not prnObj.running:
            prnObj.start()
        logging.info('Printer {} on CUPS'.format(prnObj.name))
        sleep(delay)
        #Indicate printer OK
        ledsObj.off([1])
        
        ledsObj.pulse([0],fade_in_time=.1,fade_out_time=.1,n=None)
        #Checking if host anewers to cURL requests
        test_url = 'http://{}'.format(config['host'])
        status = fname = None
        while not status == 403:
            status,fname = kiocurl.get_report(test_url,config['curl_timeout'])
            #delete cURL temp  file
            try:
                os.remove(fname)
            except FileNotFoundError:
                pass
            sleep(delay)
        logging.info('Host {} responding {}'.format(config['host'],status))
        sleep(delay)
        #Indicate cURL OK
        ledsObj.off()
        sleep(delay)

    parser = argparse.ArgumentParser(description='EGL testing report kiosk')
    parser.add_argument('-c','--config',
                        #type=argparse.FileType('r'),
                        type=str,
                        metavar='file',
                        help='Name of kiosk config file. Default: kiosk.ini',
                        default='kiosk.ini'
                        )
    args = parser.parse_args()
    config = kioconfig.read_config(args.config)
    #Exit if error reading config
    if config is None:
        return(sys.exit(1))
    bcrObj=bclib.barCodeReader(port=config['bc_reader_port'], timeout =config['bc_timeout'])
    buttonsObj  = gpiolib.kioskButtons(config['button_pins'])
    ledsObj = gpiolib.kioskPWMLeds(config['led_pins'])
    prnObj = kioprinter.kioPrinter(config['printers'],testpage=True)
    delay=config['delay']
    init_kiosk()
    ledsObj.off()
    lang=config['languages'][config['default_button']]
    #delay should not be applied at startup
    last_print_time = time() - config['report_delay']
    #Start watchdog
    if config['watchdog_device'] is not None:
        try:
            wdObj=open(config['watchdog_device'],'w')
            logging.info('Watchdog enabled on {}'.format(config['watchdog_device']))
        except Exception as e:
            logging.error(e)
    else:
        logging.info('Watchdog disabled')
    
    buttonsObj.beep()
    ledsObj.off()
    ledsObj.blink(leds=[buttonsObj.activeButton],n=None,on_time=5,off_time=.5,fade_in_time=.5,fade_out_time=.5)
    while bcrObj.running:
        #Pat watchdog
        if wdObj is not None:
            print('1',file = wdObj, flush = True)
        #Check if button is pressed or timeout -ed
        if config['button_panel'] and buttonsObj.pressed():
                ledsObj.off()
                ledsObj.blink(leds=[buttonsObj.activeButton],n=None,on_time=3,off_time=.5,fade_in_time=.5,fade_out_time=.5)
                lang=config['languages'][buttonsObj.activeButton]
        #Check if barcode is scanned
        bc = bcrObj.next()
        if len(bc)>0:
            #Prevent scanning barcode if timeout not exceeded 
            if time()<last_print_time+config['report_delay']:      
                logging.info('Repeated scan {:.2f}'.format(time()-last_print_time))
            else:
                ledsObj.blink(on_time=.2,off_time=.2,fade_in_time=.1,fade_out_time=.1,n=None)
                url = (make_URL(bc))
                resp = kiocurl.get_report(url,config['bc_timeout'])
                if resp[0]==200:
                    job_id = None
                    try:
                        prnObj.cancelAllJobs(prnObj.name)
                    except Exception as e:
                        logging.error(e)
                    try:  
                        job_id = prnObj.printFile(printer=prnObj.name,filename = resp[1],title = 'Report',options ={'print-color-mode': 'monochrome'})
                        #os.popen('aplay {}.waw'.format(lang))
                        logging.info('Report: {}, jobID: {}, lang: {}, http resp.: {}, sent to {}'.format(bc,job_id,lang, resp[0], prnObj.name))
                    except Exception as e:
                        logging.error(e)
                elif resp[0]==404:
                    #Request is valid but has no tests finished
                    logging.info('Report: {} no tests, lang: {}, http resp: #{}'.format(bc,lang, resp[0]))
                    try:
                        os.popen('aplay {}.waw'.format(lang)) 
                    except Exception as e:
                        logging.error(e)
                else:
                    logging.error('HTTPresp Report: {} empty, lang: {}, http resp: #{}'.format(bc,lang, resp[0]))
                #Remove pdf from tmp dir
                try:
                    os.remove(resp[1])
                except FileNotFoundError:
                    pass
                #Wait for printer to warm up and print report. 
                sleep(config['report_delay']*2)
                ledsObj.off()
                if config['button_panel']:
                    buttonsObj.activeButton=None

if __name__=='__main__':
    try:
        main()
    except KeyboardInterrupt:
        if wdObj is not None:
            print('V',file = wdObj, flush = True)
        print("\nExiting")

