from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError


class User(AbstractUser):
    adress = models.TextField(null=True,
                              blank=True,
                              verbose_name='Физический адресс клиента')
    phone = models.CharField(max_length=18,
                             verbose_name='Номер телефона',
                             help_text='Телефон в формате +375291234567')
    email = models.EmailField(verbose_name='Почта/email',
                              unique=True,
                              blank=False)
    first_name = models.CharField(verbose_name='Имя',
                                  max_length=30,
                                  blank=False)
    last_name = models.CharField(verbose_name='Фамилия',
                                 max_length=30,
                                 blank=False)
    patronymic = models.CharField(verbose_name='Отчество',
                                  max_length=30,
                                  blank=True,
                                  help_text='Пустое поле если отчества нет')
    telegram_id = models.IntegerField(null=True)
    chat_id = models.IntegerField(null=True)


class TelegramUser(models.Model):
    user_code = models.IntegerField()
    chat_code = models.IntegerField()
    username = models.CharField(max_length=128)
    name = models.CharField(max_length=128,
                            null=True,
                            blank=True)
    surname = models.CharField(max_length=128,
                               null=True,
                               blank=True)
    patronymic = models.CharField(max_length=128,
                                  null=True,
                                  blank=True)
    address = models.TextField(null=True,
                               blank=True)
    tel = models.CharField(max_length=32,
                           null=True,
                           blank=True)
    data = models.TextField(null=True,
                            blank=True)


class Region(models.Model):
    class Meta:
        verbose_name = 'Область'
        verbose_name_plural = 'Области'

    title = models.CharField(max_length=256)

    def __str__(self):
        return str(self.title)


class Area(models.Model):
    class Meta:
        verbose_name = 'Район'
        verbose_name_plural = 'Районы'
        ordering = ['title']

    region = models.ForeignKey(Region,
                               on_delete=models.CASCADE)
    title = models.CharField(max_length=256)

    def __str__(self):
        return f'{self.region.title} > {self.title}'


class City(models.Model):
    class Meta:
        verbose_name = 'Населенный пункт'
        verbose_name_plural = 'Населенные пункты'
        ordering = ['title']

    area = models.ForeignKey(Area,
                             on_delete=models.CASCADE,
                             null=True,
                             blank=True)

    title = models.CharField(max_length=256,
                             verbose_name='Населенный пункт')

    def __str__(self):
        return f'{self.area} > {self.title}'


class DeliveryCompany(models.Model):
    class Meta:
        verbose_name = 'Компания-доставщик'
        verbose_name_plural = 'Компании-доставщики'

    name = models.CharField(max_length=256)

    def __str__(self):
        return self.name


class OutletLocation(models.Model):
    class Meta:
        verbose_name = 'Пункт самовывоза'
        verbose_name_plural = 'Пункты самовывоза'

    company = models.ForeignKey(DeliveryCompany,
                                on_delete=models.CASCADE)
    address = models.TextField()

    def __str__(self):
        return f'{self.address}'


class PersonalOrder(models.Model):
    class Meta:
        verbose_name = 'Индивидулальный заказ'
        verbose_name_plural = 'Индивидуальные заказы'

    group_order = models.ForeignKey('GroupOrder',
                                    on_delete=models.CASCADE,
                                    null=True,
                                    blank=True,
                                    verbose_name='групповой заказ')
    code = models.CharField(max_length=256, verbose_name='Код индивидуального заказа')
    # number = models.CharField(max_length=256, verbose_name='Номер индивидуального заказа')
    # creator = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    delivery_type = models.CharField(max_length=64,
                                     verbose_name='тип доставки')
    surname = models.CharField(max_length=256,
                               verbose_name='Фамилия заказчика',
                               null=True,
                               blank=True)
    creator_id = models.CharField(max_length=64,
                                  verbose_name='ID партнера')
    tel_number = models.CharField(max_length=32,
                                  verbose_name='Номер телефона')
    fio = models.CharField(max_length=256,
                           verbose_name='Фамилия Имя Отчество получателя')
    delivery_outlet = models.ForeignKey(OutletLocation,
                                        on_delete=models.SET_NULL,
                                        null=True,
                                        blank=True,
                                        verbose_name='Пункт самовывоза',
                                        help_text='Оставить пустым, если доставка до двери')
    delivery_address = models.TextField(null=True,
                                        blank=True,
                                        verbose_name='Адресс доставки до двери',
                                        help_text='Оставить пустым, если самовывоз')  # placeholder
    comment = models.CharField(max_length=255,
                               null=True,
                               blank=True,
                               verbose_name='Комментарий')

    def __str__(self):
        if not self.group_order:
            return f'Индивидуальный заказ: {self.code}, создатель: {self.creator_id}'
        else:
            return f'Индивидуальный заказ {self.code} в группе: {self.group_order.group_code}'

    def save(self, *args, **kwargs):
        if self.delivery_outlet and self.delivery_address:
            raise ValidationError('Доставка не может быть одновременно самовывозом и до двери')
        super(PersonalOrder, self).save(*args, **kwargs)


class GroupOrder(models.Model):
    class Meta:
        verbose_name = 'Груповой заказ'
        verbose_name_plural = 'Груповые заказы'

    group_code = models.CharField(max_length=256,
                                  verbose_name='Код групового заказа',
                                  null=True,
                                  blank=True)
    # creator = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    creator_id = models.CharField(max_length=64, verbose_name='ID партнера')
    delivery_type = models.CharField(max_length=64,
                                     verbose_name='тип доставки')
    fio = models.CharField(max_length=256, verbose_name='Фамилия Имя Отчество получателя')
    tel_number = models.CharField(max_length=32, verbose_name='Номер телефона')
    delivery_outlet = models.ForeignKey(OutletLocation,
                                        on_delete=models.SET_NULL,
                                        null=True,
                                        blank=True,
                                        verbose_name='Пункт самовывоза',
                                        help_text='Оставить пустым, если доставка до двери')
    delivery_address = models.TextField(null=True,
                                        blank=True,
                                        verbose_name='Адресс доставки до двери',
                                        help_text='Оставить пустым, если самовывоз')  # placeholder
    comment = models.CharField(max_length=255,
                               null=True,
                               verbose_name='Комментарий')

    def __str__(self):
        return f'{self.group_code} создатель: {self.creator_id}'

    def save(self, *args, **kwargs):
        if self.delivery_outlet and self.delivery_address:
            raise ValidationError('Доставка не может быть одновременно самовывозом и до двери')
        super(GroupOrder, self).save(*args, **kwargs)
