# In theory the generic spreadsheet to MDF generator
import pandas as pd
#from crdclib import crdclib
import argparse
from bento_meta.model import Model, Term, Property
import sys
import numpy as np
from rich.progress import Progress
import src.nodeParser
import sys

import warnings
warnings.filterwarnings("ignore")

sys.path.append('../')
from CRDCLib.src.crdclib import crdclib


def mdfBuildProperty(node, prop_info, verbose=0):
    propdict = {'handle': prop_info['prop'],
                "_parent_handle": node,
                'is_required': prop_info['isreq'],
                'value_domain': prop_info['val'],
                'desc': prop_info['desc']}
    if 'iskey' in prop_info:
        propdict['is_key'] = prop_info['iskey']
    if verbose >= 2:
        print(f"In mdfBuildProp returning the property of\n{propdict}")
    propobj = Property(propdict)
    return propobj


def mdfBuildTerm(handle, row, verbose=0):        
#def mdfBuildTerm(handle, propinfo, row, verbose=0):
    #if (type(row[propinfo['cde_id']])) is np.float64:
    if (type(row['cde_id'])) is np.float64:
        return None
    else:
        #if type(row[propinfo['cde_version']]) is np.float64:
        if type(row['cde_version']) is np.float64:
            cdeversion = None
        else:
            #cdeversion = row[propinfo['cde_version']]
            cdeversion = row['cde_version']
        #cdeinfo = crdclib.getCDEInfo(cdeid=row[propinfo['cde_id']], version=cdeversion)
        cdeinfo = crdclib.getCDEInfo(cdeid=row['cde_id'], version=cdeversion)
        if cdeinfo['cdever']:
            version = str(cdeinfo['cdever'])
        else:
            version = cdeinfo['cdever']
        
        #terminfo = {'handle': handle, 'value': cdeinfo['cdename'], 'origin_version': version, 'origin_name': 'caDSR', 'origin_id': row[propinfo['cde_id']]}
        terminfo = {'handle': handle, 'value': cdeinfo['cdename'], 'origin_version': version, 'origin_name': 'caDSR', 'origin_id': int(row['cde_id'])}
        if verbose >= 2:
            print(f"In mdfBuildTerm returingin the Term object of\n{terminfo}")
        return Term(terminfo)



def buildPropList(node, startinginfo, mappings, verbose=0):
    proplist = []
    propinfo = mappings['properties']
    node_df = startinginfo[node]
    #
    #  Set the negative defaults for the values so I'm not doing a ton if if/else
    isreq = 'No'
    iskey = 'No'
    property_type = None
    description = None
    #
    for index, row in node_df.iterrows():
        #property_name = row[propinfo['property_name'].strip()]
        property_name = row['property_name'].strip()
        if propinfo['property_req'] != 'None':
            #if row[propinfo['property_req']] is not np.nan:
            if type(row['property_req']) is not np.float64:
                #isreq = src.nodeParser.isReqParse(row[propinfo['property_req']].strip())
                isreq = src.nodeParser.isReqParse(row['property_req'].strip())

        if propinfo['property_key'] != 'None':
            #iskey = src.nodeParser.isKeyParse(row[propinfo['property_key'].strip()])
            if type(row['property_key']) is not float:
                iskey = src.nodeParser.isKeyParse(row['property_key'].strip())

        if propinfo['property_type'] != 'None':
            if type(row['property_type']) is not float:
                property_type = row['property_type'].strip()

        if propinfo['property_description'] != 'None':
            #description = row[propinfo['property_description'].strip()]
            if type(row['property_description']) is not float:
                description = row['property_description'].strip()

        proplist.append({'prop': property_name, 'isreq': isreq, 'iskey': iskey, 'val': property_type, 'desc': description})
    if verbose >= 2:
        print(f"Returning propertylist:\n{proplist}")
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
        temp_starting_info, nodelist = src.nodeParser.xlDataFramer(nodedict=nodedict, xlfile=xlfile, mappings=mappings, sheetlist=sheetlist)
        starting_info = {}
        for node, df in temp_starting_info.items():
            #print(f"PreRename for node {node}\n{df}\n")
            #print(f"Postrename\n{src.nodeParser.dfColumnRenamer(df=df, mappings=mappings)}")
            starting_info[node] = src.nodeParser.dfColumnRenamer(df=df, mappings=mappings)
        
        if args.verbose >= 2:
            for node, df in starting_info.items():
                print(f"Node: {node}\nDataframe:\n{df}\n\n")
    #sys.exit(0)
    
    # Clean out any entries where the property is missing:
    for node, temp_df in starting_info.items():
        #temp_df = temp_df[temp_df[mappings['properties']['property_name']].notna()]
        temp_df = temp_df[temp_df['property_name'].notna()]  
        starting_info[node] = temp_df

        # For QA purposes Only
        #temp_df = starting_info['Program']
        #starting_info = {}
        #starting_info['Program'] = temp_df


    #########################################################
    #                                                       #
    #                  Properties Part Deux                 #
    #                                                       #
    #########################################################
    
    #In this episode, we try the model.add_edp_term(prop, term) and see how it goes.
    if args.verbose >= 1:
            print("Adding properties the model.add_edp_term way")
            print(f"Starting Info Keys:  {list(starting_info.keys())}")
            
            
    propinfo = mappings['properties']
    #NOTE:  Removed Progress since it seems to conflict with the detection of np.int64 objects.
    #with Progress() as np:
        #nt = np.add_task("Processing nodes...", total=len(starting_info.keys()))
        #while not np.finished:
    for node in starting_info.keys():
        #np.update(nt, advance=1)
        proplist = buildPropList(node=node, startinginfo=starting_info, mappings=mappings, verbose=args.verbose)
        #pt = np.add_task(f"Processing properties for node {node}...", total=len(proplist))
        for prop in proplist:
            #np.update(pt,advance=1)
            # Make the prop object and add it to the model
            propobj = mdfBuildProperty(node=node, prop_info=prop, verbose=args.verbose)
            nodeobj = mdf.nodes[node]
            mdf.add_prop(nodeobj, propobj)
            
            # If there is a CDE, Create a term object to annotate the property
            node_df = starting_info[node]
            #prop_df = node_df.loc[node_df[propinfo['property_name']] == prop['prop']]
            prop_df = node_df.loc[node_df['property_name'] == prop['prop']]
            row = prop_df.iloc[0]
            #print(f"CDE ID is type: {type(row[propinfo['cde_id']])}")
            #if type(row[propinfo['cde_id']]) is int:
            #print(f"CDE ID is type: {type(row['cde_id'])}")
            #print(row)
            if type(row['cde_id']) in [int, np.int64]:
                #print(f"For prop {prop['prop']} this row was sent:\n{row}\n")
                termobj = mdfBuildTerm(handle=prop['prop'], row=row, verbose=args.verbose)
                if termobj is not None:
                    mdf.annotate(propobj, termobj)
                    # If EDPs have been reqeuested, add them to the property
                    if configs['edp_enums']:
                        if propobj.value_domain != 'value_set':
                            propobj.value_domain = 'value_set'
                        mdf.add_edp_term(propobj, termobj) 
                

    #print('Term/EDP Check')
    #props = mdf.props
    #for prop in props:
    #    propobj = mdf.props[prop]
    #    print(f"\nProperty:\t{prop}")
    #    if propobj.value_set is not None:
    #        print(f"Prop Value Set:\t{propobj.value_set}")
    #        print(f"Value Set attr:\t{propobj.value_set.get_attr_dict()}")
    #        if propobj.value_set.edp_terms:
    #            print(f"Value Set EDP:\t{propobj.value_set.edp_terms}")
    #            print(f"Value Set EDP[0]:\t{propobj.value_set.edp_terms[0].get_attr_dict()}")
    #    prop_concept = mdf.props[prop].concept
    #    print(f"Prop Concept:\t{prop_concept}")
    #    if prop_concept is not None:
    #        concept_terms = prop_concept.terms
    #        print(f"Concept Terms:\t{concept_terms}")
    #        print(f"Concept Dictionary:\t{prop_concept.get_attr_dict()}")
    #    print(f"Prop Terms:\t{propobj.terms}")
    #    if propobj.concept is not None:
    #        print(f"Prop Concept Terms: {propobj.concept.terms}")
    #        for key, term in propobj.concept.terms.items():
    #            print(f"Term values: {term.get_attr_dict()}")


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
                handle = f"of_{dstnode}".lower()
                dstnode = dstnode.lower()
                card = row[edgeinfo['edge_card']].lower()
                srcnode = row[edgeinfo['edge_src']].lower()
                desc = "TBD"
                edgelist.append({'handle': handle, 'multiplicity': card, 'src': srcnode, 'dst': dstnode, 'desc': desc})
                print(f"Edge list:\t{edgelist}")
            mdf = crdclib.mdfAddEdges(mdfmodel=mdf, edgelist=edgelist)

    #print(f"EDGE CHECK:  {mdf.edges.keys()}")

    #########################################################
    #                                                       #
    #                  Tags                                 #
    #                                                       #
    #########################################################
    if args.verbose >= 1:
        print('Adding tags')
    if 'taginfo' in configs:
        taginfo = configs['taginfo']
        mdf = src.nodeParser.xlTagIt(starting_info=starting_info, taginfo=taginfo, tagtag='nodetags', tagentity='node', mdf=mdf)

        
        if len(taginfo['propertytags']) >= 1:
            mdf = src.nodeParser.xlTagIt(starting_info=starting_info, taginfo=taginfo, tagtag='propertytags', tagentity='property', mdf=mdf)


    #########################################################
    #                                                       #
    #                  Printing                             #
    #                                                       #
    #########################################################
    
    if args.verbose >= 1:
        print(f"Writing files to {configs['output_file_directory']}")
    #mdfWriteModelFiles(mdf, ['Model', 'PropDefinitions', 'Terms'], configs['output_file_directory'])
    crdclib.mdfWriteModelFiles(mdf, ['Model', 'PropDefinitions', 'Terms'], configs['output_file_directory'])                
    
            


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--configfile", required=True,  help="Configuration file containing all the input info")
    parser.add_argument('-v', '--verbose', action='count', default=0, help=("Verbosity: -v main section -vv subroutine messages -vvv data returned shown"))
    parser.add_argument("-p", "--propprint", action=argparse.BooleanOptionalAction, help="Print out the properties after creation.")

    args = parser.parse_args()

    main(args)
    
    
    


