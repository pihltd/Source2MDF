# In theory the generic spreadsheet to MDF generator
import pandas as pd
from crdclib import crdclib
import argparse
import bento_mdf
from bento_meta.model import Model
import sys
import numpy as np
import json
from rich.progress import Progress

import src.nodeParser

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
    #starting_ = {} # Keys: node names, Values: Individual node dataframes


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
        if args.verbose >= 2:
            print(f"Returned nodelist: {nodelist}")
        mdf = crdclib.mdfAddNodes(mdfmodel=mdf, nodelist=nodelist)
        if args.verbose >= 2:
            print(mdf.nodes.keys())
        
    elif configs['source_sheet_type'] == 'csv':
        nodelist = src.nodeParser.csvNodeParse(configs=configs)

    #########################################################
    #                                                       #
    #                   Startign Dataframe                  #
    #                                                       #
    #########################################################
    if args.verbose >= 1:
        print("Creating staring dataframes")

    if configs['source_sheet_type'] == 'xlsx':
        starting_info = src.nodeParser.xlDataFramer(nodelist=nodelist, xlfile=xlfile, mappings=mappings, sheetlist=sheetlist)
        if args.verbose >= 2:
            for node, df in starting_info.items():
                print(f"Node: {node}\nDataframe:\n{df}\n\n")

    #########################################################
    #                                                       #
    #                  Properties                           #
    #                                                       #
    #########################################################
    if args.verbose >= 1:
        print("Adding properties")

    for node, node_df in starting_info.items():
        proplist = []
        propinfo = mappings['properties']
        for index, row in node_df.iterrows():
            # {prop:property_name, isreq: Yes or No indictating if property is required, iskey: Yes or No indicating if property is key for the node,  'val': The property data type or 'value_set' if Enums are to be added, 'desc': Property description}
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

        mdf = crdclib.mdfAddProperty(mdf, {node: proplist})
    if args.verbose >= 2:
        print(mdf.props)

    #########################################################
    #                                                       #
    #                  Terms                                #
    #                                                       #
    #########################################################
    if args.verbose >= 1:
        print("Annotating properties with terms")
    
    # {'handle': property name, 'value':cde name, 'origin_version': cde version, 'origin_name': Source of the CDE, 'origin_id':cde idenfier, 'origin_definition': CDE Definition}
    propinfo = mappings['properties']
    with Progress() as p:
        nodetask = p.add_task("Procesing nodes...", total=len(mdf.nodes.keys()))
        #proptask = p.add_task("Processing properties...", total=len(proplist))
        while not p.finished:
            #n.update(t, advance=1)
            for node in mdf.nodes.keys():
                p.update(nodetask, advance=1)
                node_df = starting_info[node]
                proplist = mdf.nodes[node].props
                #with Progress() as p:
                #    s = p.add_task("Processing properties...", total=len(proplist))
                #    while not p.finished:
                        #p.update(s, advance=1)
                for prop in proplist:
                    #p.update(proptask, advance=1)
                    prop_df = node_df[node_df[propinfo['property_name']] == prop]
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
                        terminfo = {'handle': prop, 'value': cdeinfo['cdename'], 'origin_version': cdeinfo['cdever'], 'origin_name': 'caDSR', 'origin_id': cdeid, 'origin_definition': cdeinfo['cdedef']}
                        mdf = crdclib.mdfAnnotateTerms(mdfmodel=mdf, nodename=node, propname=prop, termdict=terminfo)

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
                handle = f"of_{dstnode.lower()}"
                card = row[edgeinfo['edge_card']].lower()
                srcnode = row[edgeinfo['edge_src']]
                desc = "TBD"
                edgelist.append({'handle': handle, 'multiplicity': card, 'src': srcnode, 'dst': dstnode, 'desc': desc})
            mdf = crdclib.mdfAddEdges(mdfmodel=mdf, edgelist=edgelist)



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

        '''if len(taginfo['nodetags']) >= 1:
            #mdf = src.nodeParser.xlTagIt(starting_info=starting_info, taginfo=taginfo, tagtag='nodetags', tagentity='node', mdf=mdf)
            nodelist = mdf.nodes.keys()
            for node in nodelist: 
                node_df = starting_info[node]
                taglocationlist = taginfo['nodetags']
                for taglocation in taglocationlist:
                    for tagname, location in taglocation.items():
                        #This is where node tagging and prop tagging diverge
                        tagvalues = node_df[location].unique().tolist()
                        for tagvalue in tagvalues:
                            mdf = crdclib.mdfAddTags(mdf, 'node', node, {'key': tagname, 'value': tagvalue})'''
        
        if len(taginfo['propertytags']) >= 1:
            mdf = src.nodeParser.xlTagIt(starting_info=starting_info, taginfo=taginfo, tagtag='propertytags', tagentity='property', mdf=mdf, mappings=mappings)
            '''nodelist = mdf.nodes.keys()
            for node in nodelist:
                node_df = starting_info[node]
                taglocationlist = taginfo['propertytags']
                for taglocation in taglocationlist:
                    for tagname, location in taglocation.items():
                        #This is where node tagging and prop tagging diverge
                        proplist = mdf.nodes[node].props.keys()
                        propdflocation = mappings['properties']['property_name']
                        for prop in proplist:
                            for index, row in node_df.iterrows():
                                if row[propdflocation] == prop:
                                    tagvalue = src.nodeParser.tagValueTranslate(row[location])
                                    mdf = crdclib.mdfAddTags(mdfmodel=mdf, objecttype='property', objectkey=(node, prop), tagdict={'key': tagname, 'value': tagvalue})'''
                                
        



    #########################################################
    #                                                       #
    #                  Printing                             #
    #                                                       #
    #########################################################
    
    if args.verbose >= 1:
        print(f"Writing files to {configs['output_file_directory']}")
    crdclib.mdfWriteModelFiles(mdf, ['Model', 'PropDefinitions', 'Terms'], configs['output_file_directory'])
            
    
            


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--configfile", required=True,  help="Configuration file containing all the input info")
    parser.add_argument('-v', '--verbose', action='count', default=0, help=("Verbosity: -v main section -vv subroutine messages -vvv data returned shown"))

    args = parser.parse_args()

    main(args)