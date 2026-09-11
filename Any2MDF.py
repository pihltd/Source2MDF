# In theory the generic spreadsheet to MDF generator
import pandas as pd
#from crdclib import crdclib
import argparse
from bento_meta.model import Model, Term, ValueSet, Property
import sys
import numpy as np
from rich.progress import Progress
from bento_mdf import MDFWriter
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import json
import math

import src.nodeParser

import warnings
warnings.filterwarnings("ignore")

sys.path.append('../')
from CRDCLib.src.crdclib import crdclib


def mdfBuildProperty(node, prop_info):
    propdict = {'handle': prop_info['prop'],
                "_parent_handle": node,
                'is_required': prop_info['isreq'],
                'value_domain': prop_info['val'],
                'desc': prop_info['desc']}
    if 'iskey' in prop_info:
        propdict['is_key'] = prop_info['iskey']
    propobj = Property(propdict)
    return propobj

def mdfbuildTerm(propdict, propinfo, node_df):
    prop_df = node_df.loc[node_df[propinfo['property_name']] == propdict['prop']]
    for index, row in prop_df.iterrows():
        print(f"Name Check:  {row[propinfo['cde_id']]} Type: {type(row[propinfo['cde_id']])}")
        if type(row[propinfo['cde_id']]) is not int:
            return None
        else:
            print("Did not match any nan detection")
            cdeid = row[propinfo['cde_id']]
            if propinfo['cde_version'] != 'None':
                cdeversion = row[propinfo['cde_version']]
            else:
                cdeversion = None
            cdeinfo = getCDEInfo(cdeid=cdeid, version=cdeversion)
            #cdeinfo = crdclib.getCDEInfo(cdeid=cdeid, version=cdeversion)
            handle = propdict['prop']
            terminfo = {'handle': handle, 'value': cdeinfo['cdename'], 'origin_version': cdeinfo['cdever'], 'origin_name': 'CRDC', 'origin_id': cdeid}
            return Term(terminfo)



def mdfAddEDP2Prop(propdict, propobj, propinfo, node_df):
    if propobj.value_domain != 'value_set':
        propobj.value_domain = 'value_set'
    prop_df = node_df.loc[node_df[propinfo['property_name']] == propdict['prop']]
    for index, row in prop_df.iterrows():
        if propinfo['cde_id'] != 'None':
            cdeid = row[propinfo['cde_id']]
        else:
            cdeid = None
        if propinfo['cde_version'] != 'None':
            cdeversion = row[propinfo['cde_version']]
        else:
            cdeversion = None
        cdeinfo = crdclib.getCDEInfo(cdeid=cdeid, version=cdeversion)
        edp_handle = f"EDP_{propdict['prop']}"
        terminfo = {'handle': edp_handle, 'value': cdeinfo['cdename'], 'origin_version': cdeinfo['cdever'], 'origin_name': 'CRDC', 'origin_id': cdeid}
        terminfo2 = {'handle': propdict['prop'], 'value': cdeinfo['cdename'], 'origin_version': cdeinfo['cdever'], 'origin_name': 'caDSR', 'origin_id': cdeid}
        #print(f"Term Info : {terminfo}")
        edpobj = Term(terminfo)
        #print(f"EDP Object: {edpobj.get_attr_dict()}")
        valobj = ValueSet({'handle':propdict['prop']})
        #print(f"ValueObject: {valobj}")
        valobj.edp_terms[0] = edpobj
        #print(f"Valobject EDP Terms: {valobj.edp_terms}")
        propobj.value_set = valobj
        #print(f"Returning propobject value set {propobj.value_set.get_attr_dict()}")
        #print(f"Value Set: {propobj.value_set}")
        #print(f"Value Set Terms: {propobj.value_set.terms}")
        #print(f"Just terms: {propobj.terms}")
        #print(f"Just values: {propobj.values}")
    return propobj, terminfo2
    
    


def buildPropList(node, startinginfo, mappings):
    proplist = []
    propinfo = mappings['properties']
    node_df = startinginfo[node]
    print(f"building proplist node DF: {node_df}")
    for index, row in node_df.iterrows():
        property_name = row[propinfo['property_name'].strip()]
        if propinfo['property_req'] != 'None':
            if row[propinfo['property_req']] is not np.nan:
                isreq = src.nodeParser.isReqParse(row[propinfo['property_req']].strip())
            else:
                isreq = 'No'
        else:
            isreq = 'No'
        if propinfo['property_key'] != 'None':
            iskey = src.nodeParser.isKeyParse(row[propinfo['property_key'].strip()])
        else:
            iskey = 'No'
        if propinfo['property_type'] != 'None':
            property_type = row[propinfo['property_type'].strip()]
        else:
            property_type = None
        if propinfo['property_description'] != 'None':
            description = row[propinfo['property_description'].strip()]
        else:
            description = None
        proplist.append({'prop': property_name, 'isreq': isreq, 'iskey': iskey, 'val': property_type, 'desc': description})
    return proplist



def mdfWriteModelFiles(mdf, sectionlist, writedir):
    """
    Writes out an mdf model object to one or more YAML files.  Does some sorting to get the YAML in proper order (Handle/Version/Nodes/Properties)

    :param mdf: MDF Model Object
    :type mdf: MDF model
    :param sectionlist: A list of the sections that should be printed.  Allowed value are Model, PropDefinitions, Terms, Relationships.
    :type sectionlist: List
    :param writedir: The direcotory to write the MDF files into
    :type writedir: String
    """

    tempdict = MDFWriter(mdf).mdf
    mdfdict = {}
    allowedsectionlist = ['Handle', 'Version', 'Nodes', 'Relationships', 'PropDefinitions', 'Terms']


    #Sorts keys for order in yaml
    for entry in allowedsectionlist:
        if entry in tempdict.keys():
            mdfdict[entry] = tempdict[entry]
    for key in tempdict.keys():
        if key not in allowedsectionlist:
            mdfdict[key] = tempdict[key]

    if len(sectionlist) > 1:
        for section in sectionlist:
            if section in allowedsectionlist:
                if section != 'Model':
                    filename = f"{writedir}{mdf.handle}-model-{section.lower()}.yml"
                    printnode = {}
                    printnode[section] = mdfdict.pop(section, None)
                    print(f"Writing to file {filename}")
                    crdclib.writeYAML(filename=filename, jsonobj=printnode)
    #Now write out whatever is left.  If Model is only section, it all gets printed
    filename = f"{writedir}{mdf.handle}-model.yml"
    print(f"Writing to file {filename}")
    crdclib.writeYAML(filename=filename, jsonobj=mdfdict)
    
    
    
def getCDEInfo(cdeid, version=None):
    """Instead of the full record, this just returns the CDE Name, CDE Definition, and CDE version.  If no version is supplied, the latest version is returned.  Used mostly in conjunction with MDF models.

    :param cde_id: CDE Public identifier
    :type cde_id: Integer
    :param cde_version: The version of the CDE to be queried.  If not supplied the latest version will be returned
    :type cde_version: String, optional
    :rtype: Dictionary ('cdename':name of the CDE, 'cdedef': CDE defintion, 'cdever': CDE version)
    """

    definition = None
    cdename = None
    cdeversion = None
    '''if version in [None, np.nan, 'nan']:
        print("ID only query")
        url = "https://cadsrapi.cancer.gov/rad/NCIAPI/1.0/api/DataElement/"+str(cdeid)
    else:
        print("ID and Version query")
        url = "https://cadsrapi.cancer.gov/rad/NCIAPI/1.0/api/DataElement/"+str(cdeid)+"?version="+str(version)'''
    headers = {'accept':'application/json'}
    
    
    url = "https://cadsrapi.cancer.gov/rad/NCIAPI/1.0/api/DataElement/"+str(cdeid)

    try:
        retry = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session = requests.Session()
        session.mount('https://', adapter)
        results = session.get(url=url, headers=headers, timeout=180)
    except requests.exceptions.HTTPError as e:
        print(e)
    if results.status_code == 200:
        results = json.loads(results.content.decode())
        if results['DataElement'] is not None:
            
            '''if 'preferredName' in results['DataElement']:
                cdename = results['DataElement']['preferredName']
            else:
                cdename = results['DataElement']['longName']
            if 'preferredDefinition' in results['DataElement']:
                definition = results['DataElement']['preferredDefinition']
            else:
                definition = results['DataElement']['definition']'''
            
            cdename = results['DataElement']['longName']
            definition = results['DataElement']['definition']
            cdeversion = results['DataElement']['version']
    else:
        cdename = 'caDSR Name Error'
    returninfo = {'cdename':cdename, 'cdedef':definition, 'cdever':cdeversion}
    #print(f"Returning caSDR Info for {cdeid} Version {version} and version is {type(version)}:  {returninfo}")
    #return {'cdename':cdename, 'cdedef':definition, 'cdever':cdeversion}
    return returninfo


    
    

def main(args):

    #########################################################
    #                                                       #
    #                  prep work                            #
    #                                                       #
    #########################################################
    if args.verbose >= 1:
        print(f"Reading configuration file {args.configfile}")
    configs = crdclib.readYAML(args.configfile)
    mappings = configs['mappings']
    nodelist = []


    if args.verbose >= 1:
        print("Creating an empty MDF object")
    mdf = Model(handle=configs['model_info']['handle'], version=configs['model_info']['version'])

    if configs['source_sheet_type'] == 'xlsx':
        xlfile = pd.ExcelFile(configs['source_sheet_file'])
        sheetlist = xlfile.sheet_names
        for sheet in mappings['excluded_tabs']:
            sheetlist.remove(sheet)

    #########################################################
    #                                                       #
    #                  Nodes                                #
    #                                                       #
    #########################################################
        if args.verbose >= 1:
            print("Adding Nodes")
    
        nodelist = src.nodeParser.xlNodeParse(sheetlist=sheetlist, mappings=mappings, xlfile=xlfile)
        nodedict = {}
        for node in nodelist:
            nodedict[node.lower()] = node
        nodelist = [x.lower() for x in nodelist]
        if args.verbose >= 2:
            print(f"Returned nodelist: {nodelist}")
            print(f"Nodedict: {nodedict}")
        mdf = crdclib.mdfAddNodes(mdfmodel=mdf, nodelist=nodelist)
        if args.verbose >= 2:
            print(f"Model nodes: {mdf.nodes.keys()}")
        
    elif configs['source_sheet_type'] == 'csv':
        nodelist = src.nodeParser.csvNodeParse(configs=configs)
        nodelist = [x.lower() for x in nodelist]

    #########################################################
    #                                                       #
    #                   Startign Dataframe                  #
    #                                                       #
    #########################################################
    if args.verbose >= 1:
        print("Creating staring dataframes")

    if configs['source_sheet_type'] == 'xlsx':
        starting_info, nodelist = src.nodeParser.xlDataFramer(nodedict=nodedict, xlfile=xlfile, mappings=mappings, sheetlist=sheetlist)
        if args.verbose >= 2:
            for node, df in starting_info.items():
                print(f"Node: {node}\nDataframe:\n{df}\n\n")
    
    # Clean out any entries whre the property is missing:
    for node, temp_df in starting_info.items():
        temp_df = temp_df[temp_df[mappings['properties']['property_name']].notna()]
        #Force the columns, properties, and domains to lowercase
        temp_df[mappings['nodes']].str.lower()
        temp_df[mappings['properties']['property_name']].str.lower()
        temp_df[mappings['domains']].str.lower()
        starting_info[node] = temp_df
    
    print(f"Starting DF:\n{starting_info}")
        

        # For QA purposes Only
        #temp_df = starting_info['Program']
        #starting_info = {}
        #starting_info['Program'] = temp_df

    #########################################################
    #                                                       #
    #                  Properties                           #
    #                                                       #
    #########################################################
    
    # In the era of EDPs, this needs a rethink since the ENUM is an addition to the property.
    
    if args.verbose >= 1:
        print("Adding properties")
        print(f"Starting Info Keys:  {list(starting_info.keys())}")
        
    for node in starting_info.keys():
        proplist = buildPropList(node=node, startinginfo=starting_info, mappings=mappings)
        for prop in proplist:
            if configs['edp_enums'] == 'True':
                #Oddly, need to add the EDP info first since the annotate function works at the model lever
                propobj = mdfBuildProperty(node=node, prop_info=prop)
                propobj, terminfo = mdfAddEDP2Prop(propdict=prop, propobj=propobj, propinfo=mappings['properties'], node_df=starting_info[node])
                #print(f"Propobj: {propobj}")
                #print(f"Terms: {propobj.terms}")
                #print(f"Values: {propobj.values}")
                #print(f"Node: {node}\t Prop: {prop['prop']}\t Obj: {propobj}\tHandle: {propobj.handle}\nTerm Info: {terminfo}")
                termobj = Term(terminfo)
                #valobj = ValueSet({'hanlde':prop['prop']})
                #valobj.edp_terms[0] = termobj
                #propobj.value_set = valobj
                nodeobj = mdf.nodes[node]
            else:
                propobj = mdfBuildProperty(node=node, prop_info=prop)
                nodeobj = mdf.nodes[node]
                mdf.add_prop(nodeobj, propobj)
                #Now deal with the Term
                termobj = mdfbuildTerm(propdict=prop, propinfo=mappings['properties'], node_df=starting_info[node])
                
                
            mdf.add_prop(nodeobj, propobj)
           
            # Then need to add the Term.  Currently this is VERY fragile, but it will do for now.
            print(f"Term is {termobj} and type {type(termobj)}")
            if termobj is not None:
                mdf.annotate(propobj, termobj)
            
            
            if args.verbose >= 3:
                thisprop = mdf.props[(node,prop['prop'])]
                print(f"The Prop: {thisprop}")
                print(f"Prop Info: {thisprop.get_attr_dict()}")
                print(f"Prop Value Set: {thisprop.value_set}")
                print(f"Pprop Value Set Terms: {thisprop.value_set.terms}")
                print(f"Prop Value Set Terms Items: {thisprop.value_set.items()}")
                print(f"Prop Terms: {thisprop.terms}")
                print(f"Prop Values: {thisprop.values}")
                print(f"Prop Concepts: {thisprop.concept}")
                print(f"Prop Concept Terms: {thisprop.concept.terms}")
                print(f"Prop Concept Term Items: {thisprop.concept.terms.items()}")
                for key, term in thisprop.concept.terms.items():
                    print(f"Term values: {term.get_attr_dict()}")

 


    #########################################################
    #                                                       #
    #                  Edges                                #
    #                                                       #
    #########################################################
    # Relationships need to be in a separate tab (xlsx) or separate fils (csv)
    if args.verbose >= 1:
        print("Adding relationships")

    # {'handle': A name forthe edge, 'multiplicity': one-to-one, many-to-one, ect, 'src': the name of the source node, 'dst': the name of the destination node, 'desc': a description of the edge}
    edgeinfo = mappings['edge_info']
    if configs['source_sheet_type'] == 'xlsx':
        edge_df = pd.read_excel(xlfile, edgeinfo['edge_info_source'])
        dstnodes = edge_df[edgeinfo['edge_dst']].unique().tolist()
        if args.verbose >= 2:
            print(f"DST node list: {dstnodes}")
        for dstnode in dstnodes:
            edgelist = []
            dst_df = edge_df[edge_df[edgeinfo['edge_dst']] == dstnode]
            for index, row in dst_df.iterrows():
                handle = f"of_{dstnode}"
                card = row[edgeinfo['edge_card']]
                srcnode = row[edgeinfo['edge_src']]
                desc = "TBD"
                edgelist.append({'handle': handle, 'multiplicity': card, 'src': srcnode, 'dst': dstnode, 'desc': desc})
            mdf = crdclib.mdfAddEdges(mdfmodel=mdf, edgelist=edgelist)

    print(f"EDGE CHECK:  {mdf.edges.keys()}")

    #########################################################
    #                                                       #
    #                  Tags                                 #
    #                                                       #
    #########################################################
    if args.verbose >= 1:
        print('Adding tags')
    if 'taginfo' in configs:
        taginfo = configs['taginfo']
        mdf = src.nodeParser.xlTagIt(starting_info=starting_info, taginfo=taginfo, tagtag='nodetags', tagentity='node', mdf=mdf, mappings=mappings)

        
        if len(taginfo['propertytags']) >= 1:
            mdf = src.nodeParser.xlTagIt(starting_info=starting_info, taginfo=taginfo, tagtag='propertytags', tagentity='property', mdf=mdf, mappings=mappings)


    #########################################################
    #                                                       #
    #                  Printing                             #
    #                                                       #
    #########################################################
    
    if args.verbose >= 1:
        print(f"Writing files to {configs['output_file_directory']}")
    mdfWriteModelFiles(mdf, ['Model', 'PropDefinitions', 'Terms'], configs['output_file_directory'])
    #crdclib.mdfWriteModelFiles(mdf, ['Model', 'PropDefinitions', 'Terms'], configs['output_file_directory'])                
    
            


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--configfile", required=True,  help="Configuration file containing all the input info")
    parser.add_argument('-v', '--verbose', action='count', default=0, help=("Verbosity: -v main section -vv subroutine messages -vvv data returned shown"))

    args = parser.parse_args()

    main(args)
    
    
    


