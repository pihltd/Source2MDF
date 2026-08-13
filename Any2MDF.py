# In theory the generic spreadsheet to MDF generator
import pandas as pd
#from crdclib import crdclib
import argparse
from bento_meta.model import Model
import sys
import numpy as np
from rich.progress import Progress

import src.nodeParser

sys.path.append('../')
from CRDCLib.src.crdclib import crdclib
    
def mdfAddEDPEnum(mdfmodel, nodename, propname, termdictlist):
    """ The new EDP (Extended Data Property) feature requires that both a Term section and an Enum section exist for a property.
    The Term section serves to indicate what the property is, and the Enum section now allows a Term-like object to define an MDB list of permissible values.

    :para mdf: A valid MDF model
    :type mdf: An MDF model object
    :param nodename: The name of the node the property belongs to 
    :type nodename: String
    :param propname: The name of the proptery to be annotated with an Enum
    :type propname: String
    :param termdict: A list of dictionary containg the same information a a Term:  [{'handle': property name, 'value':cde name, 'origin_version': cde version, 'origin_name': Source of the CDE, 'origin_id':cde idenfier, 'origin_definition': CDE Definition}]
    :type termdict: Python list
    :return: An updated MDF model object
    :rtype: MDF model object
    """

    if nodename in list(mdfmodel.nodes):
        if (nodename, propname) in list(mdfmodel.props):
            propobj = mdfmodel.props[nodename, propname]
            termlist = []
            for termdict in termdictlist:
                termobj = Term(termdict)
                #termlist.append(Term(termdict))
            #if propobj.value_domain != 'value_set':
            #    propobj.value_domain = 'value_set'
            if propobj.value_domain != 'enum':    #If value domain is set to enum, the only thing that happens is Type is set to enum.
                propobj.value_domain = 'enum'
                mdfmodel.annotate(propobj, termobj) #Borks with a message that the term already exists
            #mdfmodel.add_terms(propobj, termobj)
            #mdfmodel.add_terms(propobj, *termlist)
            #mdfmodel.add_terms(propobj, *termdictlist)  Borks with not a term object
    return mdfmodel

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
    nodecount = 0
    propcount = 0
    with Progress() as p:
        nodetotal = len(mdf.nodes.keys())
        proptotal = len(mdf.props.keys())
        
        print(f"Nodetotal is {nodetotal}")
        nodetask = p.add_task("Procesing nodes...", total=nodetotal)
        proptask = p.add_task("Processing properties...", total=proptotal)
        for node in mdf.nodes.keys():
            node_df = starting_info[node]
            proplist = mdf.nodes[node].props
            for prop in proplist:
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
                propcount = propcount+1
                p.update(task_id=proptask, completed=propcount+1)
            nodecount = nodecount+1
            p.update(task_id=nodetask, completed=nodecount+1)



    #########################################################
    #                                                       #
    #                  EDP Enum                             #
    #                                                       #
    #########################################################
    if configs['edp_enums']:
        if args.verbose >= 1:
            print("Adding EDP Enum sections to properties")
        propinfo = mappings['properties']
        nodecount = 0
        propcount = 0
        with Progress() as pb:
            nodetotal = len(mdf.nodes.keys())
            proptotal = len(mdf.props.keys())
            nodetask = p.add_task("Procesing EDP Nodes...", total=nodetotal)
            proptask = p.add_task("Processing EDP Props...", total=proptotal)
            for node in mdf.nodes.keys():
                node_df = starting_info[node]
                proplist = mdf.nodes[node].props
                for prop in proplist:
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
                        #terminfo = {'handle': prop, 'value': cdeinfo['cdename'], 'origin_version': cdeinfo['cdever'], 'origin_name': 'caDSR', 'origin_id': cdeid, 'origin_definition': cdeinfo['cdedef']}
                        #terminfo = {'value': cdeinfo['cdename'], 'origin_version': cdeinfo['cdever'], 'origin_name': 'caDSR', 'origin_id': cdeid, 'origin_definition': cdeinfo['cdedef']}
                        #thingamabob = str({'value': cdeinfo['cdename'], 'origin_version': cdeinfo['cdever'], 'origin_name': 'caDSR', 'origin_id': cdeid, 'origin_definition': cdeinfo['cdedef']})
                        #terminfo = {'handle':thingamabob}
                        terminfo = {'handle': prop, 'value': cdeinfo['cdename'], 'origin_version': cdeinfo['cdever'], 'origin_name': 'caDSR', 'origin_id': cdeid}
                        mdf = mdfAddEDPEnum(mdfmodel=mdf, nodename=node, propname=prop, termdictlist=[terminfo])
                    propcount = propcount+1
                    p.update(task_id=proptask, completed=propcount+1)
                nodecount = nodecount+1
                p.update(task_id=nodetask, completed=nodecount+1)






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

        
        if len(taginfo['propertytags']) >= 1:
            mdf = src.nodeParser.xlTagIt(starting_info=starting_info, taginfo=taginfo, tagtag='propertytags', tagentity='property', mdf=mdf, mappings=mappings)


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