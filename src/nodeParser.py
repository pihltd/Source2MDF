import pandas as pd
import sys
from crdclib import crdclib
import numpy as np

def trimList(inputlist):
    outputlist = []
    for entry in inputlist:
        outputlist.append(entry.strip())
    return outputlist



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

def xlDataFramer(nodelist, xlfile, mappings, sheetlist):
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

    for nodename in nodelist:
        if mappings['nodes'] == 'tab':
            temp_df = pd.read_excel(xlfile, nodename)
            final[nodename] = temp_df
        else:
            temp_df = pd.read_excel(xlfile, sheetlist[0])
            node_df = temp_df[temp_df[mappings['nodes'].strip()] == nodename]
            final[nodename] = node_df
    return final

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
            for node in nodelist: 
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
                            propdflocation = mappings['properties']['property_name']
                            for prop in proplist:
                                for index, row in node_df.iterrows():
                                    if row[propdflocation] == prop:
                                        tagvalue = tagValueTranslate(row[location])
                                        mdf = crdclib.mdfAddTags(mdfmodel=mdf, objecttype=tagentity, objectkey=(node, prop), tagdict={'key': tagname, 'value': tagvalue})
                        else:
                            print(f"{tagentity} is not a recognized MDF object type")
                            sys.exit(0)

                            
    return mdf


