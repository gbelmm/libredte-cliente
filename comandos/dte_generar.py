# -*- coding: utf-8 -*-

"""
LibreDTE
Copyright (C) SASCO SpA (https://sasco.cl)

Este programa es software libre: usted puede redistribuirlo y/o modificarlo bajo
los términos de la Licencia Pública General Affero de GNU publicada por la
Fundación para el Software Libre, ya sea la versión 3 de la Licencia, o (a su
elección) cualquier versión posterior de la misma.

Este programa se distribuye con la esperanza de que sea útil, pero SIN GARANTÍA
ALGUNA; ni siquiera la garantía implícita MERCANTIL o de APTITUD PARA UN
PROPÓSITO DETERMINADO. Consulte los detalles de la Licencia Pública General
Affero de GNU para obtener una información más detallada.

Debería haber recibido una copia de la Licencia Pública General Affero de GNU
junto a este programa.
En caso contrario, consulte <http://www.gnu.org/licenses/agpl.html>.
"""

"""
Comando para generar un DTE a partir de los datos de JSON o un XML
@author Esteban De La Fuente Rubio, DeLaF (esteban[at]sasco.cl)
@version 2017-12-29
"""

# módulos usados
from base64 import b64encode, b64decode
import os
from json import dumps as json_encode
from json import loads as json_decode
import codecs
import sys

# opciones en formato largo
long_options = ['json=', 'xml=', 'archivo=', 'formato=', 'encoding=', 'cedible=', 'papel=', 'web=', 'dir=', 'normalizar=', 'getXML', 'email', 'cotizacion']

# función principal del comando
def main(Cliente, args, config) :
    json, xml, archivo, formato, encoding, cedible, papel, web, dir, normalizar, getXML, email, cotizacion = parseArgs(args)
    data = None
    if json :
        data = loadJSON(json, encoding)
        formato = 'json'
    if xml :
        data = loadXML(xml, encoding)
        formato = 'xml'
    if archivo != None and formato != None and formato not in ('json', 'xml') :
        data = '"'+b64encode(bytes(loadFile(archivo, encoding), 'UTF8')).decode('UTF8')+'"'
    if data == None :
        print('Debe especificar un archivo JSON o bien un archivo XML a enviar')
        return 1
    if not dir :
        print('Debe especificar un directorio de salida para los archivos a generar')
        return 1
    # crear directorio para archivos si no existe
    if not os.path.exists(dir):
        os.makedirs(dir)
    # crear DTE temporal
    emitir_url = '/dte/documentos/emitir?normalizar='+str(normalizar)+'&formato='+formato
    if cotizacion == 1 and email == 1 :
        emitir_url += '&email='+str(email)
    emitir = Cliente.post(emitir_url, data)
    if emitir.status_code!=200 :
        print('Error al emitir DTE temporal: '+json_encode(emitir.json()))
        return emitir.status_code
    try :
        with open(dir+'/temporal.json', 'w') as f:
            f.write(json_encode(emitir.json()))
    except ValueError :
        print('Error al recibir JSON DTE temporal, se recibió: '+emitir.text)
        return 1
    # crear DTE real sólo si no es cotización
    if cotizacion == 0 :
        generar = Cliente.post('/dte/documentos/generar?getXML='+str(getXML)+'&email='+str(email), emitir.json())
        if generar.status_code!=200 :
            print('Error al generar DTE real: '+json_encode(generar.json()))
            return generar.status_code
        try :
            dte_emitido = generar.json()
        except ValueError :
            print('Error al recibir JSON DTE real, se recibió: '+generar.text)
            return 1
        xml_emitido = dte_emitido['xml']
        dte_emitido['xml'] = None
        with open(dir+'/emitido.json', 'w') as f:
            f.write(json_encode(dte_emitido))
        if getXML :
            with codecs.open(dir+'/emitido.xml', 'w', 'iso-8859-1') as f:
                f.write(b64decode(xml_emitido).decode('iso-8859-1'))
        columnas = ['emisor', 'dte', 'folio', 'certificacion', 'tasa', 'fecha', 'sucursal_sii', 'receptor', 'exento', 'neto', 'iva', 'total', 'usuario', 'track_id']
        valores = []
        for col in columnas :
            if dte_emitido[col] != None :
                valores.append(str(dte_emitido[col]))
            else :
                valores.append('')
        with open(dir+'/emitido.csv', 'w') as f:
            f.write(';'.join(columnas)+"\n")
            f.write(';'.join(valores)+"\n")
        # obtener el PDF del DTE
        generar_pdf = Cliente.get('/dte/dte_emitidos/pdf/'+str(generar.json()['dte'])+'/'+str(generar.json()['folio'])+'/'+str(generar.json()['emisor'])+'?cedible='+str(cedible)+'&papelContinuo='+str(papel))
        if generar_pdf.status_code!=200 :
            print('Error al generar PDF del DTE: '+json_encode(generar_pdf.json()))
            return generar_pdf.status_code
        # guardar PDF en el disco
        with open(dir+'/emitido.pdf', 'wb') as f:
            f.write(generar_pdf.content)
    # si es cotización bajar el PDF
    else :
        cotizacion_pdf = Cliente.get('/dte/dte_tmps/pdf/'+str(emitir.json()['receptor'])+'/'+str(emitir.json()['dte'])+'/'+str(emitir.json()['codigo'])+'/'+str(emitir.json()['emisor'])+'&cotizacion=1&papelContinuo='+str(papel))
        if cotizacion_pdf.status_code!=200 :
            print('Error al generar PDF de la cotización: '+json_encode(cotizacion_pdf.json()))
            return cotizacion_pdf.status_code
        with open(dir+'/cotizacion.pdf', 'wb') as f:
            f.write(cotizacion_pdf.content)
    # todo ok
    return 0

# función que procesa los argumentos del comando
def parseArgs(args) :
    json = ''
    xml = ''
    archivo = None
    formato = None
    encoding = 'UTF-8'
    cedible = 1
    papel = 0
    web = False
    dir = ''
    normalizar = 1
    getXML = 0
    email = 0
    cotizacion = 0
    for var, val in args:
        if var == '--json' :
            json = val
        elif var == '--xml' :
            xml = val
        elif var == '--archivo' :
            archivo = val
        elif var == '--formato' :
            formato = val
        elif var == '--encoding' :
            encoding = val
        elif var == '--cedible' :
            cedible = val
        elif var == '--papel' :
            papel = val
        elif var == '--web' :
            web = val
        elif var == '--dir' :
            dir = val
        elif var == '--normalizar' :
            normalizar = val
        elif var == '--getXML' :
            getXML = 1
        elif var == '--email' :
            email = 1
        elif var == '--cotizacion' :
            cotizacion = 1
    return json, xml, archivo, formato, encoding, cedible, papel, web, dir, normalizar, getXML, email, cotizacion

# función que carga un JSON
def loadJSON (archivo, encoding) :
    return json_decode(loadFile(archivo, encoding))

# función que carga un XML
def loadXML (archivo, encoding) :
    return '"'+b64encode(bytes(loadFile(archivo, encoding), 'UTF8')).decode('UTF8')+'"'

# función que carga un archivo
def loadFile (archivo, encoding) :
    if encoding == 'UTF-8' :
        try :
            with open(archivo, 'r') as content_file:
                content = content_file.read()
            return content
        except UnicodeDecodeError :
            print('No fue posible leer el archivo por codificación ¿asignar --encoding?')
            sys.exit(1)
    else :
        content = ''
        fd = codecs.open(archivo, 'r', encoding)
        for line in fd :
            content += line
        fd.close()
        return content
