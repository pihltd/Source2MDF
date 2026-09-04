# In theory the generic spreadsheet to MDF generator
import pandas as pd
#from crdclib import crdclib
import argparse
from bento_meta.model import Model, Term, ValueSet, Property
import sys
import numpy as np
from rich.progress import Progress

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

def mdfAddEDP2Prop(propdict, propobj, propinfo, node_df):
    if propobj.value_domain != 'value_set':
        propobj.value_domain = 'value_set'
    #print(f"Starting propobject value set{propobj.value_set.terms}")
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
        # For QA purposes Only
        temp_df = starting_info['Program']
        starting_info = {}
        starting_info['Program'] = temp_df

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
            
            mdf.add_prop(nodeobj, propobj)
           
            # Then need to add the Term.  Currently this is VERY fragile, but it will do for now.
            mdf.annotate(propobj, termobj)
            
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
    
    
    
'''for node, node_df in starting_info.items():
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
            
        #print(f"Node: {node}\nProplist: {proplist}")
        for prop in proplist:
            print(f"Working prop: {prop}")
            propobj = mdfBuildProperty(node=node, prop_info=prop)
            print(f"Prop object: {propobj}")
            #node_df = starting_info[node]
            print(f"Node DF:\n {node_df}")
            #print(f"Propinfo key: {propinfo['property_name']}")
            #print(f"Whole Propinfo: {propinfo}")
            prop_df = node_df[node_df[propinfo['property_name']] == prop]
            #prop_df = node_df.query("Property == @prop")
            print(f"Prop DF: \n{prop_df}")
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
                terminfo = {'handle': prop, 'value': cdeinfo['cdename'], 'origin_version': cdeinfo['cdever'], 'origin_name': 'caDSR', 'origin_id': cdeid}
                nodeobj = mdf.nodes[node]
                edpobj = Term(terminfo)
                valobj = ValueSet({'handle':prop})
                valobj.edp_terms[0] = edpobj
                propobj.value_set = valobj
                mdf.add_prop(nodeobj, propobj)'''
                
            
        #mdf = crdclib.mdfAddProperty(mdf, {node: proplist})
    #if args.verbose >= 2:
    #    print(mdf.props)

    #########################################################
    #                                                       #
    #                  Terms                                #
    #                                                       #
    #########################################################
'''if args.verbose >= 1:
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
            p.update(task_id=nodetask, completed=nodecount+1)'''



    #########################################################
    #                                                       #
    #                  EDP Enum                             #
    #                                                       #
    #########################################################
'''if configs['edp_enums']:
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
                        #mdf = mdfAddEDPEnum(mdfmodel=mdf, nodename=node, propname=prop, termdictlist=[terminfo])
                        print(terminfo)
                        mdf = mdfAddEDP(mdfmodel=mdf, nodename=node, propname=prop, edppdict=terminfo)
                    propcount = propcount+1
                    p.update(task_id=proptask, completed=propcount+1)
                nodecount = nodecount+1
                p.update(task_id=nodetask, completed=nodecount+1)
'''


