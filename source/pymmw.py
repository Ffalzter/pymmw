#!/bin/sh
'''which' python3 > /dev/null && exec python3 "$0" "$@" || exec python "$0" "$@"
'''

#
# Copyright (c) 2018, Manfred Constapel
# This file is licensed under the terms of the MIT license.
#

#
# goto pymmw 
#

import os
import sys
import glob
import serial
import threading
import json
import argparse
import signal
import platform
import time

from lib.shell import *
from lib.probe import *
from lib.carrier import *

# ------------------------------------------------

def _init_(data, fw):
    # Testprint
    #print("\nGehe in _init\n")

    global mss

    # Testprint
    #print("\n!!!! -> Bin in _init_ und printe fw: " + str(fw))

    if len(data) > 0 and mss is None:

        # Testprint
        print("\nBin in _init_, Länge der Daten ist: " + str(len(data)) + "!!!\n")

        for item in fw:
            mss = __import__(item, fromlist=('',))

            # Testprint
            print("!!!! -> Bin in der for-Schleife von _init_ und printe mss nach dem import der Firmware! mss: " +
                  str(mss) + ", vom Typ: " + str(type(mss)) + "!!!\n")


            if len(mss._read_(data, open(os.devnull, "w"))) > 1:

                # Testprint
                #print("\n!!! pymmw.py _init_ TRUE !!!\n")
                print(mss._read_(data, open(os.devnull, "w"))) # hier wird von mss das entsprechende dev (xWR64xx) geprintet

                return True
            mss = None

    # Testprint
    #print("\nBin in _init_ und printe den Rückgabewert: False\n")
    return False


def _read_(prt, dat, timeout=2, handle=None):  # observe control port and call handler when firmware is recognized
    """
    myDoc:
    This function is called as a Thread in the _main_ of pymmw.py.

    """

    # Testprint
    #print("\n--- Bin in _read_ von pymmw!!!\n")

    #  script_path get the path of the directory of pymmw.py
    script_path = os.path.dirname(os.path.realpath(sys.argv[0]))
    # Testprint
    #print("\nAus _read_ printe script_path:\n" + script_path)

    # In fw the names of .py files in the \pymmw\source\mss directory are getting saved in these steps.
    fw = [os.path.splitext(item)[0].split(os.sep) for item in glob.glob(os.sep.join((script_path, 'mss', '*.py')))]
    fw = ['.'.join(mss[-2:]) for mss in fw]
    # Testprint
    #print("\nPrinte fw aus _read_:\nfw = " + str(fw))

    cnt = 0
    ext = {}

    try:
        
        if len(fw) == 0:
            raise Exception('no handlers found')
        
        t = time.time()
        # Testprint
        #print("\nPrinte t (time.time) aus Thread _read_.\nt= " + str(time.asctime(time.localtime(t))) + "\n")

        data = ''

        reset = None

        
        while handle is None:
            # The serial connection 'prt' is read out. readline() read until EOL (end-of-line) character
            # terminate reading process. decode() returns a decoded string (type str).
            # (myDoc)
            data = prt.readline().decode('latin-1')
            # Testprint
            #print(data)


            if _init_(data, fw):  # firmware identified

                # Testprint
                print("\n!!!! -> Bin in if '_init_' vom Thread '_read_' !!!!\n")

                # Testprint
                print("\n!!!! -> DATAPRINT! Printe die Daten, die jetzt da sind:\n" + str(data))

                handle = data.strip() # removes spaces from decoded string

                # Testprint
                print("!!!! -> handle hat einen neuen Wert: " + str(handle) + " <-----!!!!\n")

                break
            else:
                # (myDoc) Hier bleibt das Programm scheinbar solange, bis nrst betätigt wird,
                # da noch keine Daten über den Control-Port (COM4) laufen
                print(data, end='', flush=True)
                # Testprint
                print("\n_init_ ist False\n")
  

            # Scheinbar geht das Programm niemals in die nachfolge if-Schleife, da timeout als 'None' gesetzt ist.
            # Ich glaube, dass das hier nur verwendet wird, wenn man DCA1000 oder mmWaveBost benutzt.
            # MMWAVEBOST AND DCA1000 ONLY ----> (*FTDI_USB, check carrier.py)
            if timeout is not None:
                if time.time() - timeout > t:
                    car = usb_discover(*FTDI_USB)
                    if len(car) > 0 and not reset:
                        reset = time.time()
                        if not ftdi_reset(*FTDI_USB):
                            raise Exception('carrier not supported')
                        t = reset
                        continue
                    raise Exception('no handler found')

        # End of while
        # The while-loop ends when nrst is pressed, data comes over control-port (COM4), mss gets name of firmware-file,
        # and handle is not False

        # Testprint
        print("\nStatus von mss nachdem handle nicht mehr None ist: " + str(mss) + "\n")
        if mss is None:
            if not _init_(handle, fw):
                raise Exception('handler not supported')                

        reset = None

        while True:
            buf = mss._read_(data) # die Funktion gibt das Gerät zurück (in meinem Fall xWR64xx), warum nicht xWR68xx ?

            # Testprint
            #print("\n!!! -> Handle nicht mehr None und bin jetzt in der unteren while-Schleife von _read_")
            #print("!!! -> pymmw.py _read_: Inhalt von data, mit dem mss ausgelesen wird: " + str(data))
            #print("!!! -> Ich printe jetzt 'buf': " + str(buf) + " <- !!!\n")
            
            if len(buf) < 2:
                if reset:  # reset detected
                    handler = os.path.splitext(mss.__file__.split(os.sep)[-1])[0]

                    # Testprint
                    print("\nBin in der unteren While-Schleife von _read_ und gehe in die 'if len(buf) < 2'-Schleife" +
                          " und der handler wird ausgelsen! handler: " + str(handler) + "\n")

                    print_log('handler:', handler, '-', 'configuration:', reset) # (i) handler: x8_mmw - configuration: xWR64xx
                    cnt += 1

                    file = open('{}/{}-{}.{}'.format('mss', handler, reset, 'cfg'), 'r') # hier bastelt der sich mss/x8_mmw-xWR64xx.cfg zusammen
                    # Testprint
                    print("File soll geladen werden: " + str(file))

                    content = load_config(file)
                    # Testprint
                    #print("Folgender Content soll geladen werden:\n" + str(content))

                    cfg = json.loads(content) # hier lädt der die x8_mmw-xWR64xx.cfg Datei (JSON)
                    # Test
                    #print("Folgende Configuration soll geladen werden:\n" + str(cfg))

                    cfg, par = mss._conf_(cfg)
                    # holt sich hier aus der cfg die entsprechenden Werte raus und löscht einige Einträge und schreibt
                    # die "neue" cfg dann in die Variable cfg (überschreibt diese). In der Variable 'par' werden Werte
                    # reingeschrieben, die aus der 'cfg' genommen mit Hilfe dieser berechnet wurden ('loglin', 'fftcomp', 'rangebias')

                    mss._init_(prt, dev, cfg, dat) # °!A<"S§hier wird Thread gestartet, der den Datenport ausliest (prt,dev,cfg werden gar nicht benutzt)
                    mss._proc_(cfg, par)
                    send_config(prt, cfg, mss._read_)
                    show_config(cfg)
                reset = None # reset ist zuvor xWR64xx und wird hier zurückgesetzt, sodass diese if-Schleife erstmal nicht betreten wird
                # Testprint
                print("\npymmw.py _read_ unten -> RESET WIRD ZURÜCKGESETZT!!!!")
            else:
                # Testprint
                print("\npymmw.py _read_ in letzter ELSE: buf hat eine Länge größer als 2,bin daher in der else und , printe reset = buf = " + str(buf))
                reset = buf

            data = prt.readline().decode('latin-1')
            # Testprint
            print("\nPrinte data ganz unten in pymmw.py _read_: " + str(data) + " | (Ende)")
            
    except Exception as e:
        print_log(e, sys._getframe())
        os._exit(1)
            

def _input_(prt):  # accept keyboard input and forward to control port
    """
    Diese Funktion ist scheinbar dafür da, Eingaben über die Tastur zu empfangen und diese an der Sensor
    zu senden. Um ein CLI Kommando für den Sensor zu sein, müssen die Eingaben mit einem % beginnen.
    """
    # Testprint
    print("\n--- Bin in _input_ von pymmw!!!\n")

    while not sys.stdin.closed:
        line = sys.stdin.readline()   
        if not line.startswith('%'):
            prt.write(line.encode())

# ------------------------------------------------

if __name__ == "__main__":

    # Testprint
    print("\nBetrete __name__ = __main__\n")
    #
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    nrst = 'Windows' not in platform.system()

    # Testprint
    print("\nIch printe VARIABLE nrst aus __main__: " + str(nrst) + "\n")

    try:
        # Testprint
        #print("\nIch betrete in __name__ die try Anweisung\n")

        # Das hier ist dafür da, um das Programm aus eine Shell starten zu können.
        # Es werden die Argumente generiert, die eingesetzt werden, um die Ports zu definieren
        parser = argparse.ArgumentParser(description='pymmw', epilog='', add_help=True, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        
        parser.add_argument('-c', '--control-port', help='serial port for control communication', required=not nrst or '-n' in sys.argv or '--no-discovery' in sys.argv)
        parser.add_argument('-d', '--data-port', help='serial port auxiliary communication', required=not nrst or '-n' in sys.argv or '--no-discovery' in sys.argv)
        parser.add_argument('-f', '--force-handler', help='force handler for data processing (disables autodetection)', required=False)
        parser.add_argument('-n', '--no-discovery', help='no discovery for USB devices (avoids pre-access to the XDS debug probe)', action='store_true')        

        # Hier werden die Argumente des Parsers (aus der Shell vermutlich) in
        # die Variable args übergeben
        args = parser.parse_args()
        # Testprint
        print("\nIch printe ARGS aus dem try von __main__: " + str(args) + "\n")

        # ---
        
        dev, prts = None, (None, None)
        # Testprint
        print("\nIch printe DEV und PRTS aus der __main__: " + str(dev) + str(prts) + "\n")

        nrst = nrst and not args.no_discovery
        # Testprint
        print("\nIch printe args.no_discovery aus __main__: " + str(args.no_discovery))
        print("\nIch printe VARIABLE nrst aus __main__ erneut: " + str(nrst) + "\n")


        if nrst:
            # Testprint
            print("\nIch bin in der IF NRST\n")
            try:
                dev = usb_discover(*XDS_USB)

                # Testprint
                print("\nIch bin in dem try nach IF NRST!\nIch printe Variable dev:\n" + str(dev))

                if len(dev) == 0: raise Exception('no device detected')
         
                dev = dev[0]
                print_log(' - '.join([dev._details_[k] for k in dev._details_]))
 
                for rst in (False,):
                    try:
                        xds_test(dev, reset=rst)
                        break
                    except:
                        pass
                     
                prts = serial_discover(*XDS_USB, sid=dev._details_['serial'])
                if len(prts) != 2: raise Exception('unknown device configuration detected')
         
            except:
                nrst = False
                # Testprint
                print("\nBin in der except von IF NRST\n")

        # ---

        if args.control_port is None: args.control_port = prts[0]
        if args.data_port is None: args.data_port = prts[1]        
        
        # ---
        
        mss = None

        # Hier wird der Controlport (COM4) seriell ausgelesen bzw. eine Verbindung aufgebaut.
        # Diese wird dann im Thread für _read_ verwendet, um die Daten auszulesen
        con = serial.Serial(args.control_port, 115200, timeout=0.01)
        # Testprint
        print("\nPrinte con aus der __main__\n" + str(con) + "\n")

        if con is None: raise Exception('not able to connect to control port')

        print_log('control port: {} - data port: {}'.format(args.control_port, args.data_port))

        # Testprint
        print("\nTestprint, ob ich nach dem print_log noch printen kann!\nIch print args.force_handler: " +
              str(args.force_handler))

        if args.force_handler:
            print_log('handler: {}'.format(args.force_handler))

        # Der geht scheinbar hier in diese beiden Threads rein, die die target-Funktionen starten, und wartet dort,
        # bis ich was mache
        tusr = threading.Thread(target=_read_, args=(con, args.data_port, None if not nrst else 2, args.force_handler))
        tusr.start()

        tstd = threading.Thread(target=_input_, args=(con,), )
        tstd.start()
        # Testprint
        print("\nIch bin hier nach dem Starten der Threads und will überprüfen, ob ich diesen Bereich erreiche, nachdem die Threads starten\n")
        # ---
        
        if nrst:
            # Testprint
            print("\nIch bin in der IF-ANWEISUNG VON NRST = TRUE\n")
            xds_reset(dev)
            usb_free(dev)
        else:
            print('\nwaiting for reset (NRST) of the device', file=sys.stderr, flush=True)



    except Exception as e:
        # Testprint
        print("\nIch bin in dem except von __main__\n")
        print_log(e, sys._getframe())
        os._exit(1)
