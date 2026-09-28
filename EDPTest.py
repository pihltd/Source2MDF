import bento_mdf
from crdclib import crdclib
import sys
#sys.path.append('../')
#from CRDCLib.src.crdclib import crdclib


#sourcefiles = [r'C:\Users\pihltd\Documents\VMShare\modeltest\SDM-model.yml', r'C:\Users\pihltd\Documents\VMShare\modeltest\SDM-model-propdefinitions.yml']
sourcefiles = [r'C:\Users\pihltd\Documents\VMShare\modeltest\TEST_SDM-model.yml', r'C:\Users\pihltd\Documents\VMShare\modeltest\TEST_SDM-model-propdefinitions.yml']

#mdf = bento_mdf.MDF(*sourcefiles, resolve_edps=True)
mdf = bento_mdf.MDF(*sourcefiles)
mdf = mdf.model


print(f"Handle: {mdf.handle}\tVersion: {mdf.version}")


nodes = mdf.nodes

for node in nodes:
    for prop in nodes[node].props:
        print(f"Node {node}\tProp: {prop}")
        edpstuff = crdclib.mdfGetEnumInfo(mdf=mdf, nodename=node, propname=prop)
        if edpstuff is not None:
            print(f"EDP Stuff: {edpstuff[0]}")
        termstuff = crdclib.mdfGetTermInfo(mdf=mdf, nodename=node, propname=prop)
        if termstuff is not None:
            print(f"Term Stuff: {termstuff[0]}")

#terms = mdf.model.terms
#terms = mdf.terms

#for term in terms:
#    print(term)
#    print(terms[term].get_attr_dict())
    

#props = mdf.model.props
#props = mdf.props
#print(props)
#for prop, propobj in props.items():
#    print(f"Prop Key: {prop} Prop Object: {propobj}")
#    print(f"Prop value domain: {propobj.value_domain}")
#    if propobj.concept is not None:
#        print(f"Prop obj term: {propobj.concept.terms}")
#        print(f"Prop obje concept term value {propobj.concept.terms.items()}")
#    print(f"Prop Value Set: {propobj.value_set}")
#    if propobj.value_set is not None:
#        print(f"EDP_terms: {propobj.value_set.edp_terms}")
#        print(f"EDP_terms values: {propobj.value_set.edp_terms.items()}")
#        for key, value in propobj.value_set.edp_terms.items():
#            print(f"EDP Key: {key}\tEDP Values: {value.get_attr_dict()}")
