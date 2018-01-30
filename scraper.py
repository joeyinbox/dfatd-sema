import logging
import requests
from lxml import etree
from normality import collapse_spaces

from libsanctions import Source, Entity, BirthDate

log = logging.getLogger(__name__)
XML_URL = 'http://www.international.gc.ca/sanctions/assets/office_docs/sema-lmes.xml'  # noqa



def parse():
    res = requests.get(XML_URL)
    doc = etree.fromstring(res.content)
    source = Source('dfatd-sema')

    for node in doc.findall('.//record'):
        parse_entry(source, node)

    source.finish()



def parse_entry(source, node):
    # ids are per country and entry type (individual/entity)
    country = get_country(node)
    id = str(node.findtext('.//Item'))
    
    if node.findtext('.//Entity') is None:
        type = 'ind'
    else:
        type = 'ent'
    
    entity = source.create_entity(country+'-'+type+'-'+id)
    
    if country is not None:
        nationality = entity.create_nationality()
        nationality.country = country
    
    if type is 'ind':
        parse_individual(entity, node)
    else:
        parse_entity(entity, node)
    
    parse_alias(entity, node)
    parse_schedule(entity, node)
    entity.save()



def parse_individual(entity, node):
    entity.type = Entity.TYPE_INDIVIDUAL
    entity.firstname = node.findtext('.//GivenName')
    entity.lastname = node.findtext('.//LastName')
    
    # Some entities do not have all name parts
    parts = []
    if entity.firstname is not None:
        parts.append(entity.firstname)
    if entity.lastname is not None:
        parts.append(entity.lastname)
    entity.name = ' '.join(parts)

    parse_dob(entity, node)



def parse_entity(entity, node):
    entity.type = Entity.TYPE_ENTITY
    
    # Some entities have French translations
    names = node.findtext('.//Entity').split('/')
    entity.name = names.pop(0)
    
    # Save them as aliases
    if len(names) > 0:
        for name in names:
            entity.create_alias(name=name)



def parse_dob(entity, node):
    dob = node.findtext('.//DateOfBirth')
    if dob is None:
        return
    
    birth_date = entity.create_birth_date()
    
    if '/' not in dob:
        birth_date.date = dob
        birth_date.quality = BirthDate.QUALITY_WEAK
    else:
        day, month, year = dob.split('/', 2)
        birth_date.date = year+'-'+month+'-'+day
        birth_date.quality = BirthDate.QUALITY_STRONG



def get_country(node):
    names = node.findtext('.//Country')
    if names is None:
        return None
    
    # Only keep english version
    name = names.split(' / ')[0]
    name = collapse_spaces(name)
    if not len(name):
        return None
    
    return name



def parse_alias(entity, node):
    names = node.findtext('.//Aliases')
    if names is None:
        return
    
    for name in names.split(', '):
        name = collapse_spaces(name)
        if not len(name):
            continue
        
        # Some aliases have multiple parts
        parts = name.split('/')
        for part in parts:
            entity.create_alias(name=part)



def parse_schedule(entity, node):
    schedule = node.findtext('.//Schedule')
    if schedule is None or schedule is 'N/A':
        return
    
    entity.summary = 'Schedule '+schedule



if __name__ == '__main__':
    parse()
