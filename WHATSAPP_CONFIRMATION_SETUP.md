# WhatsApp Onay Mesaji Kurulumu

Bu dokuman, rezervasyon `CONFIRMED` oldugunda musterinin WhatsApp numarasina otomatik "rezervasyonunuz onaylandi" mesaji gondermek icin gerekli kurulumu anlatir.

## Ne Zaman Calisir

Bu entegrasyon iki durumda otomatik tetiklenir:

- Musteri public onay linkine girip rezervasyonu onayladiginda
- Admin panelde rezervasyon durumu `CONFIRMED` yapildiginda

Mesaj gonderimi basarisiz olsa bile rezervasyon durumu geri alinmaz. Yani rezervasyon yine onayli kalir.

## Gerekenler

Bu ozellik normal bireysel WhatsApp ile degil, **Meta WhatsApp Business Cloud API** ile calisir.

Gerekenler:

- Meta Business hesabi
- WhatsApp Business Account (WABA)
- Dogrulanmis business telefon numarasi
- Cloud API icin `Access Token`
- `Phone Number ID`
- Onaylanmis bir WhatsApp message template

## Template Yapisi

Backend su anda 4 degiskenli bir template bekliyor.

Onerilen template adi:

```text
reservation_confirmed
```

Onerilen dil:

```text
tr
```

Onerilen govde:

```text
Merhaba {{1}},
rezervasyonunuz onaylandi.
PNR: {{2}}
Transfer saati: {{3}}
Rota: {{4}}
```

Backend bu alanlari su sirayla doldurur:

1. Musterinin adi soyadi
2. PNR kodu
3. Transfer tarihi ve saati
4. Rota ozeti

## .env Ayarlari

`.env` dosyaniza asagidaki alanlari ekleyin:

```env
WHATSAPP_ENABLED=true
WHATSAPP_GRAPH_API_VERSION=v23.0
WHATSAPP_ACCESS_TOKEN=your-whatsapp-cloud-api-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
WHATSAPP_CONFIRMATION_TEMPLATE_NAME=reservation_confirmed
WHATSAPP_CONFIRMATION_TEMPLATE_LANGUAGE=tr
WHATSAPP_DEFAULT_COUNTRY_CODE=90
```

Alan aciklamalari:

- `WHATSAPP_ENABLED`: Ozelligi acip kapatir
- `WHATSAPP_GRAPH_API_VERSION`: Meta Graph API versiyonu
- `WHATSAPP_ACCESS_TOKEN`: Meta tarafindan verilen yetkili token
- `WHATSAPP_PHONE_NUMBER_ID`: Mesajin hangi business numaradan gidecegi
- `WHATSAPP_CONFIRMATION_TEMPLATE_NAME`: Onaylanmis template adi
- `WHATSAPP_CONFIRMATION_TEMPLATE_LANGUAGE`: Template dili
- `WHATSAPP_DEFAULT_COUNTRY_CODE`: Telefon numarasinda ulke kodu yoksa varsayilan kod

## Telefon Numarasi Formati

Backend telefon numarasini normalize etmeye calisir.

Desteklenen tipik formatlar:

- `+90555...`
- `90555...`
- `0555...`
- `00 90 555 ...`

Varsayilan ulke kodu `90` oldugu icin, Turkiye numaralarinda genelde sorun yasamazsiniz.

## Kurulum Adimlari

1. Meta tarafinda WhatsApp Cloud API kurulumunu tamamlayin.
2. Mesaj gonderen business numarayi aktif edin.
3. `reservation_confirmed` adinda template olusturun.
4. Template onayini bekleyin.
5. `.env` dosyasina gerekli degerleri yazin.
6. API servisini restart edin.

## Nasil Test Edilir

En saglikli test akisi:

1. Gecerli bir musteri telefonu ile rezervasyon olusturun.
2. Rezervasyonu ya public confirm linkinden onaylayin ya da admin panelden `CONFIRMED` yapin.
3. Musteri telefonunda WhatsApp mesaji geldigini kontrol edin.

Alternatif olarak admin panelden test:

1. `/admin/login` ile giris yapin
2. Rezervasyon detayina girin
3. Durumu `CONFIRMED` secin
4. `Degisiklikleri kaydet` butonuna basin

## Nerede Tetikleniyor

Kodda tetiklenen noktalar:

- `app/services/booking_service.py`
- `app/services/admin_booking_service.py`
- `app/services/whatsapp_service.py`

## Hata Durumlari

Mesaj gitmiyorsa en yaygin nedenler:

- `WHATSAPP_ENABLED=false`
- Token gecersiz
- `PHONE_NUMBER_ID` hatali
- Template adi birebir eslesmiyor
- Template dili yanlis
- Musteri numarasi WhatsApp kullanmiyor
- Meta hesabi/template henuz tam onayli degil

## Onemli Not

Mevcut entegrasyon su anda **template message** gonderir. Serbest metin gonderimi kullanilmiyor.
Bu bilincli bir tercih; cunku rezervasyon onayi sistemsel bir bildirimdir ve daha stabil calisir.
