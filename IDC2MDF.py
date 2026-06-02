from bento_mdf import MDFWriter
from bento_meta.model import Model
import argparse
import pandas as pd
import requests
import json

from bento_meta.model import Node, Property, Term, Tag, Edge
from bento_mdf.validator import MDFValidator
from jsonschema import SchemaError, ValidationError
from yaml.parser import ParserError
from IPython.display import clear_output

#import sys
#sys.path.append('../CRDCLib/')
# from src.crdclib import crdclib
from crdclib import crdclib


def cleanHTML(inputstring):
    outputstring = inputstring.replace("<br>", "")
    return outputstring


def validateModel(filelist):
    try:
        MDFValidator(*filelist, raise_error=True).load_and_validate_schema()
    except SchemaError as e:
        clear_output()
        print(f"Schema error:\n{e}")


def getCDEInfo(cdeid, version=None, verbose=0):
    definition = None
    cdename = None
    cdeversion = None
    if version is None:
        url = "https://cadsrapi.cancer.gov/rad/NCIAPI/1.0/api/DataElement/"+str(cdeid)
    else:
        url = "https://cadsrapi.cancer.gov/rad/NCIAPI/1.0/api/DataElement/"+str(cdeid)+"?version="+str(version)
    headers = {'accept':'application/json'}

    if verbose >= 2:
        print(f"caDSR URL:\n{url}")
    try:
        results = requests.get(url, headers = headers)
    except requests.exceptions.HTTPError as e:
        print(e)
    if results.status_code == 200:
        results = json.loads(results.content.decode())
        if results['DataElement'] is not None:
            if verbose >= 3:
                print(f"Return caDSR JSON:\n{results['DataElement']}")
            if 'preferredName' in results['DataElement']:
                cdename = results['DataElement']['preferredName']
            else:
                cdename = results['DataElement']['longName']
            if 'preferredDefinition' in results['DataElement']:
                definition = results['DataElement']['preferredDefinition']
            else:
                definition = results['DataElement']['definition']
            cdeversion = results['DataElement']['version']
    else:
        cdename = 'caDSR Name Error'
    if definition is not None:
        definition = crdclib.cleanString(definition, True)
    return {'cdename':cdename, 'cdedef':definition, 'cdever':cdeversion}



def addProps(datamodel, nodedict, add_node=False):
    node_prop_dict = {}
    edgelist = []
    for node, workign_df in nodedict.items():
        node_prop_dict[node] = []
        for index, row in workign_df.iterrows():
            valtype = 'string'
            req = 'No'
            if pd.notnull(row['Description']):
                description = crdclib.cleanString(str(row['Description']), True)
                description = cleanHTML(description)
            else:
                description = None
            if pd.notnull(row['Property']):
                tempinfo = {}
                propname = crdclib.cleanString(row['Property'], True)
                propname = cleanHTML(propname)
                propname = propname.lower()
                if row['Required/optional'] == 'R':
                    req = 'Yes'
                    #req = True
                tempinfo = {'prop': propname, "_parent_handle": node, 'isreq': req, 'val': valtype, 'desc': description}
                if row['Key'] == 'yes':
                    tempinfo['iskey'] = 'True'
                node_prop_dict[node].append(tempinfo)
    datamodel = crdclib.mdfAddProperty(datamodel, node_prop_dict, False)
    return datamodel, edgelist





def addTerms(datamodel, nodedict, verbose=0):
    for nodename, working_df in nodedict.items():
        for index, row in working_df.iterrows():
            if 'Recommended CDE' in row:
                if pd.notnull(row['Recommended CDE']):
                    cdeinfo = crdclib.getCDEInfo(row['Recommended CDE'])
                    if cdeinfo['cdedef'] is not None:
                        cdedef = crdclib.cleanString(cdeinfo['cdedef'],True)
                        cdedef = cleanHTML(cdedef)
                    else:
                        cdedef = None
                    cdeid = str(row['Recommended CDE'])
                    # For some reason, IDs out of Excel are formated like a float
                    cdeid = cdeid.split(".")[0]
                    termvalues = {'handle': row['Property'].lower(), 'value': cdeinfo['cdename'], 'origin_version': cdeinfo['cdever'], 'origin_name':'caDSR', 'origin_id':cdeid, 'origin_definition': cdedef, 'nanoid': 'cdeurl'}
                    datamodel = crdclib.mdfAnnotateTerms(datamodel, nodename, row['Property'], termvalues)
                elif 'Permissible values' in row:
                    if pd.notnull(row['Permissible values']):
                      pvlist = row['Permissible values'].split("\n")
                      datamodel = crdclib.mdfAddEnums(mdfmodel=datamodel, nodename=nodename, propname=row['Property'], enumlist=pvlist)
    return datamodel



def writeFiles(mdf, configs, sectionlist, verbose=0):
    # This writes out the separate mode, property, etc., if reuested in the config.
    jsonobj = json.dumps(MDFWriter(mdf).mdf)
    tempdict = json.loads(jsonobj)

    mdfdict = {}
    allowedsectionlist = ['Handle', 'Version', 'Nodes', 'Relationships', 'PropDefinitions', 'Terms']
    handle = 'nci_imaging_submission'
    
    if verbose >=1:
        print("Sorting final model sections")

    #Sorts keys for order in yaml
    for entry in allowedsectionlist:
        if entry in tempdict.keys():
            mdfdict[entry] = tempdict[entry]
    # Any remaining keys are added at the end
    for key in tempdict.keys():
        if key not in allowedsectionlist:
            mdfdict[key] = tempdict[key]

    filenamelist = configs['mdffiles']
    if len(configs['mdffiles']) >= 1:
        for section in sectionlist:
            if section in allowedsectionlist:
                if section != 'Model':
                    for file in filenamelist:
                        if section in file:
                            filename = file[section]
                          
                    printfilename = f"{configs['workingpath']}{filename}"
                    printnode = {}
                    printnode[section] = mdfdict.pop(section, None)
                    crdclib.writeYAML(filename=printfilename, jsonobj=printnode)
    #After printing out the requested sections, print out what's left
    for entry in configs['mdffiles']:
        for mdfsection, filename in entry.items():
            if mdfsection == 'Model':
                crdclib.writeYAML(configs['workingpath']+filename, mdfdict)



def addEdges(datamodel, edgelist, verbose=0):
    if verbose >= 2:
        print(f"Starting Edge list:\n{edgelist}")
    listofedges = []
    for edge in edgelist:
        if verbose >= 2:
            print(f"Adding edge: {edge}")
        for end in edge['ends']:
            listofedges.append({'handle':edge['handle'], 'multiplicity':edge['mul'], 'src': end['src'], 'dst':end['dst'], 'desc': edge['desc']})
    if verbose >= 2:
        print(f"Complete set of edges to add:\n{listofedges}")
    datamodel = crdclib.mdfAddEdges(datamodel, listofedges)
    return datamodel



def addTags(datamodel, taglist, verbose=0):
    for tag in taglist:
        for tagname, tagvalue in tag.items():
            tagname = tagname.lower()
            if verbose >= 2:
                print(f"Datamodel: {datamodel}\nNode: {tag['node'].lower()}\n TagName: {tagname}\nTagValue: {tagvalue}\n")
            datamodel = crdclib.mdfAddTags(datamodel, 'node', tag['node'].lower(), {'key':tagname, 'value':tagvalue})
    return datamodel

        

def main(args):
    # Setup
    if args.verbose >= 1:
        print("Config and dictionary setup")
    configs = crdclib.readYAML(args.configfile)
    nodedict = {}

    #Read the input file
    if args.verbose >= 1:
        print(f"Reading Excel file {configs['excelfile']}")
    xlfile = pd.ExcelFile(configs['workingpath']+configs['excelfile'])

    #Get the node names (sheet names)
    if args.verbose >= 1:
        print("Setting up node/dataframe dictionary")
    for node in xlfile.sheet_names:
        if node == configs['edgesheet']:
            if args.verbose >= 2:
                print('Populating edge_df')
            edge_df = pd.read_excel(configs['workingpath']+configs['excelfile'], node)
        elif node not in configs['excludetabs']:
            temp_df = pd.read_excel(configs['workingpath']+configs['excelfile'], node)
            nodedict[node.lower()] = temp_df
    
    # Create an empty model object
    if args.verbose >= 1:
        print("Setting up an empty model")
    idc_mdf = Model(handle= configs['handle'], version= configs['version'])

    # Add nodes
    if args.verbose >= 1:
        print('Adding nodes to the model')
    idc_mdf = crdclib.mdfAddNodes(idc_mdf, list(nodedict.keys()))

    print(f"Nodes from model: {idc_mdf.nodes.keys()}")
    
    # Add properties
    if args.verbose >= 1:
        print("Adding properties to the model")
    idc_mdf, edgelist = addProps(idc_mdf, nodedict, False)

    # Add terms
    if args.verbose >= 1:
        print('Adding CDE Terms to model')
    idc_mdf = addTerms(idc_mdf, nodedict, args.verbose)

    #Add node tags
    if args.verbose >=1:
        print('Adding tags to nodes')
    if 'tags' in configs:
        idc_mdf = addTags(idc_mdf, configs['tags'], args.verbose )

    # Add edges
    if args.verbose >= 1:
        print("Adding edges to model")
    edgelist = []
    for index, row in edge_df.iterrows():
        edgelist.append({
        'handle': f"of_{row['Destination node'].lower()}",
        'desc': f"Data of {row['Destination node'].lower()}",
        'mul': row['Cardinality'],
        'ends': [{'src': row['Source node'].lower(), 'dst': row['Destination node'].lower()}]
        })

    idc_mdf = addEdges(idc_mdf, edgelist, args.verbose)

    # Write out the files
    if args.verbose >= 1:
        print(f"Writing out the MDF Files in {configs['workingpath']}")
    sectionlist = ['Model', 'PropDefinitions', 'Terms']
    #writeFiles(idc_mdf, configs, sectionlist, args.verbose)
    crdclib.mdfWriteModelFiles(idc_mdf, sectionlist, configs['workingpath'])

    if args.verbose >= 1:
        print("Validating final model")
    filelist = []
    for fileentry in configs['mdffiles']:
        for filename in fileentry.values():
            filelist.append(f"{configs['workingpath']}{filename}")
    validateModel(filelist)

    if configs['loadsheetpath'] is not None:
        if args.verbose >= 1:
            print(f"Writing data load sheets in {configs['loadsheetpath']}")
        load_df = crdclib.mdfBuildLoadSheets(idc_mdf, reverse=False, typecolumn=True)
        for node, loadsheet_df in load_df.items():
            filename = f"{configs['loadsheetpath']}NCI_Imaging_Data_Loading_Template_{node}.tsv"
            loadsheet_df.to_csv(filename, sep="\t", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--configfile", required=True,  help="Configuration file containing all the input info")
    parser.add_argument('-v', '--verbose', action='count', default=0, help=("Verbosity: -v main section -vv subroutine messages -vvv data returned shown"))

    args = parser.parse_args()

    main(args)
