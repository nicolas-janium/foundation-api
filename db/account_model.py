from db.base_model import Base

class Account(Base):
    __tablename__ = 'account'
    unassigned_account_id = '8acafb6b-3ce5-45b5-af81-d357509ba457'

    def __init__(self, account_id, account_group_id, email_config_id,
                       is_sending_emails, is_sending_li_messages, is_receiving_dte,
                       effective_start_date, effective_end_date, data_enrichment_start_date,
                       data_enrichment_end_date, time_zone_id, updated_by, account_type_id):
        self.account_id = account_id
        self.account_group_id = account_group_id
        self.email_config_id = email_config_id
        self.is_sending_emails = is_sending_emails
        self.is_sending_li_messages = is_sending_li_messages
        self.is_receiving_dte = is_receiving_dte
        self.effective_start_date = effective_start_date
        self.effective_end_date = effective_end_date
        self.data_enrichment_start_date = data_enrichment_start_date
        self.data_enrichment_end_date = data_enrichment_end_date
        self.time_zone_id = time_zone_id
        self.updated_by = updated_by
        self.account_type_id = account_type_id

    account_id = Column(String(36), primary_key=True)

    account_type_id = Column(Integer, ForeignKey('account_type.account_type_id'), nullable=False)
    account_group_id = Column(String(36), ForeignKey('account_group.account_group_id'), nullable=False)
    # ulinc_config_id = Column(String(36), ForeignKey('ulinc_config.ulinc_config_id'), nullable=False)
    # email_config_id = Column(String(36), ForeignKey('email_config.email_config_id'), nullable=False)
    time_zone_id = Column(String(36), ForeignKey('time_zone.time_zone_id'), nullable=False)

    is_sending_emails = Column(Boolean, server_default=false(), nullable=False)
    is_sending_li_messages = Column(Boolean, server_default=false(), nullable=False)
    is_receiving_dte = Column(Boolean, server_default=false(), nullable=False)

    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    effective_start_date = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    effective_end_date = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    data_enrichment_start_date = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    data_enrichment_end_date = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # SQLAlchemy Relationships and Backreferences
    # users = relationship('User_account_map', back_populates='account')
    # users = relationship('User_account_map')
    janium_campaigns = relationship('Janium_campaign', backref=backref('janium_campaign_account', uselist=False), uselist=True, lazy='dynamic')
    ulinc_campaigns = relationship('Ulinc_campaign', backref=backref('ulinc_campaign_account', uselist=False), uselist=True, lazy='dynamic')
    contacts = relationship('Contact', backref=backref('contact_account', uselist=False), uselist=True, lazy='dynamic')
    # email_config = relationship('Email_config', backref=backref('email_config_account', uselist=False), uselist=False, lazy=True)
    ulinc_configs = relationship('Ulinc_config', backref=backref('ulinc_config_account', uselist=False), uselist=True, lazy=True)
    time_zone = relationship('Time_zone', backref=backref('tz_account', uselist=True), uselist=False, lazy=True)