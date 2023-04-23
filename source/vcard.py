import vobject

vCard = vobject.vCard()
vCard.add('N').value = vobject.vcard.Name(given='ThumbTings')
vCard.add('FN').value = "ThumbTings"

vCard.add('EMAIL')
vCard.email.value = 'thumbtings@gmail.com'
vCard.email.type_param = 'INTERNET'

vCard.add('TEL')
vCard.tel.value = '+1-609-908-4970'
vCard.tel.type_param = 'HOME'

with open('ThumbTings.vcf', 'w') as writer:
  writer.write(vCard.serialize())
