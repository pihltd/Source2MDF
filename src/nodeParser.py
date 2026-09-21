import pandas as pd
import sys
from crdclib import crdclib
import numpy as np

def trimList(inputlist):
    #print(f"InputList: {inputlist}")
    outputlist = []
    for entry in inputlist:
        #entry = entry.lower()
        if ";" in entry:
            entry = entry.split(";")[0]
        #print(f"Trimlist Entry: {entry}")
        elif ":" in entry:
            entry = entry.split(":")[0]
        if entry not in outputlist:
            outputlist.append(entry.strip())
    #print(f"Returned list: {outputlist}")
    return outputlist



def dfColumnRenamer(df, mappings):
    # Rather than muck about with individual column names, rename them to simple names
    changedict = {}
    for key, info in mappings.items():
        if key == 'node':
            if mappings['nodes'] != 'tab':
                changedict[info] = key
        elif key == 'properties':
            for new, old in mappings['properties'].items():
                if mappings['properties'][new] != 'None':
                    changedict[old] = new
        elif key == 'edge_info':
            for new,old in mappings['edge_info'].items():
                if mappings['edge_info'][new] != 'None':
                    changedict[old] = new
    df.rename(columns=changedict, inplace=True)
    
    #df['cde_id'] = df['cde_id'].apply(lambda x: x.replace('TBD', np.nan))
    for index, row in df.iterrows():
        if row['cde_id'] == 'TBD':
            df.at[index, 'cde_id'] = None
    
    #print(df)
    
    
    #Now cast some columns to known datatypes
    astypedict = {
        'property_name': str,
        'property_req': str,
        'property_key': str,
        'property_type': str,
        'property_description': str,
        'cde_id': int
    }
    
    nokeylist = []
    # For any column being converted to int, need to turn any NaN into 0
    df[['cde_id']] = df[['cde_id']].fillna(0)
    for key in astypedict.keys():
        if key not in df.columns:
            nokeylist.append(key)
    for key in nokeylist:
        astypedict.pop(key)
    
    df = df.astype(astypedict)
    '''
    for field, datatype in astypedict.items():
        if field in df:
            df = df[field].astype(datatype)
    #df['nodes'] = df['nodes'].astype(str)
    #df['property_name'] = df['property_name'].astype(str)
    #df['property_req'] = df['property_req'].astype(str)
    #df['property_key'] = df['property_key'].astype(str)
    #if 'property_type' in df.columns:
    #    df['property_type'] = df['property_type'].astype(str)
    #df['property_description'] = df['property_description'].astype(str)
   # 
    #df['cde_id'] = df['cde_id'].astype(int)
    #df['cde_version']
    '''
    return df


def xlNodeParse(sheetlist, mappings, xlfile):
    """Parses nodes from the source file and returns a list of nodes

    :param sheetlist: A list of all the tabs in the excel workbook
    :type sheetlist: Python list
    :param mappings: The mapping section from the config file
    :type mapping: Python dictionary
    :type xlfile:  Object from reading the excel file wtih pd.ExcelFile
    :return: A python list of node names
    :rtype: Python list
    """

    if len(sheetlist) == 1:
        # This is the easy one
        xl_df = pd.read_excel(xlfile, sheetlist[0])
        if mappings['nodes'] in xl_df.columns:
            return trimList(xl_df[mappings['nodes']].unique().tolist())
        else:
            print(f"{mappings['nodes']} is not a valid column name in the spreadsheet")
            sys.exit(0)
    elif len(sheetlist) > 1:
        if mappings['nodes'] == 'tab':
            #Node names are the tab names which we got as input so just give it back.
            return trimList(sheetlist)
    else:
        print("Something has gone horribly wrong with the node parsing")
        sys.exit(0)


def csvNodeParse(configs):
    """Parses a CSV file and returns a list of nodes
    :param configs: The parsed config file
    :type configs: Python dictionary
    :return: Python list of node names
    :rtype: Python list    
    """
    separators = {'tab':"\t", 'comma':","}
    source_df = pd.read_csv(configs['source_sheet_file'], sep=separators[configs['source_sheet_delimiter']])
    return trimList(source_df[configs['node']].unique().tolist())

def xlDataFramer(nodedict, xlfile, mappings, sheetlist, verbose=0):
    """Reads an Excel workbook and returns a dictionary of dataframes
    
    :param nodelist: List of nodes in the model
    :type nodelist: Python list
    :param xlfile: Excel file parsed with pd.ExcelFile
    :type xlfile: Excel object
    :param mappings: The mapping section of the parsed configuration file
    :type mappings: Python dictionary
    :return: Python dictionary.  Keys are node names, values are dataframes
    :rtype: Python dictionary"""

    final = {}
    newnodelist = []
    for lcnodename, ucnodename in nodedict.items():
        if mappings['nodes'] == 'tab':
            temp_df = pd.read_excel(xlfile, ucnodename)
            if verbose >= 2:
                print(f"UC Nodename: {ucnodename}\nTemp Dataframe:\n{temp_df}\n")
            final[lcnodename] = temp_df
        else:
            temp_df = pd.read_excel(xlfile, sheetlist[0])
            node_df = temp_df[temp_df[mappings['nodes'].strip()] == ucnodename]
            if not node_df.empty:
                final[lcnodename] = node_df
                newnodelist.append(lcnodename)
    return final, newnodelist

def isReqParse(isreq):
    isreqoptions = {
        'R': 'Yes',
        'O': 'No',
        'CR': 'No',
        'DCR': 'No',
        'P': 'No',
        'nan': 'No'
    }

    if isreq in isreqoptions:
        return isreqoptions[isreq]
    else:
        return 'No'
    
def isKeyParse(iskey):
    iskeyoptions = {
        'yes': 'Yes'
    }
    if iskey in iskeyoptions:
        return iskeyoptions[iskey]
    else:
        return 'No'
    
def tagValueTranslate(tagvalue):
    """Generic lookup and translation dictionary service"""

    translations = {
        'Y': 'Yes',
        'N': 'No',
        'N - SRF': 'No',
        np.nan: 'No'
    }

    if tagvalue in translations:
        return translations[tagvalue]
    else:
        print(f"{tagvalue} does not map")
        return tagvalue


def xlTagIt(starting_info, taginfo, tagtag, tagentity, mdf, mappings=None):
    """Adds tags to things in the model
    
    :param starting_info: The dictionary of dataframes
    :type starting_info: Python dictionary of dataframse
    :param taginfo: The taginfo section of the config file
    :type taginfo: Python dictionary of lists
    :param tagtag: The dictionary key for taginfo
    :type tagtag: String
    :param tagentity: The entity type to be tagged.  Node, property, etc.
    :type tagentity: String
    :param mdf: The MDF model object
    :type mdf: MDF Model object
    :param mappings: Mappings section from the config file
    :type mappings: Python dictionary
    :return: An MDF model object
    :rtype: MDF model object"""

    if len(taginfo[tagtag]) >= 1:
            nodelist = mdf.nodes.keys()
            #print(f"xlTagIT nodelist: {nodelist}")
            #print(f"xlTagIT starting info keys: {list(starting_info.keys())}")
            for node in nodelist:
                if node in starting_info.keys(): 
                    node_df = starting_info[node]
                    taglocationlist = taginfo[tagtag]
                    for taglocation in taglocationlist:
                        for tagname, location in taglocation.items():
                            if tagentity == 'node':
                                tagvalues = node_df[location].unique().tolist()
                                for tagvalue in tagvalues:
                                    mdf = crdclib.mdfAddTags(mdfmodel=mdf,objecttype=tagentity, objectkey=node, tagdict={'key': tagname, 'value': tagvalue})
                            elif tagentity == 'property':
                                proplist = mdf.nodes[node].props.keys()
                                #propdflocation = mappings['properties']['property_name']
                                for prop in proplist:
                                    for index, row in node_df.iterrows():
                                        #if row[propdflocation] == prop:
                                        if row['property_name'] == prop:
                                            tagvalue = tagValueTranslate(row[location])
                                            mdf = crdclib.mdfAddTags(mdfmodel=mdf, objecttype=tagentity, objectkey=(node, prop), tagdict={'key': tagname, 'value': tagvalue})
                            else:
                                print(f"{tagentity} is not a recognized MDF object type")
                                sys.exit(0)

                            
    return mdf


