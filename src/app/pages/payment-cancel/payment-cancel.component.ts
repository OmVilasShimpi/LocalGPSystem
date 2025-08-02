import { Component } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-payment-cancel',
  standalone: true,
  imports:[TranslateModule],
  templateUrl: './payment-cancel.component.html',
  styleUrls: ['./payment-cancel.component.css']
})
export class PaymentCancelComponent {
  constructor(public translate: TranslateService) {
  const supportedLangs = ['en', 'hin', 'fr', 'de', 'pl'];
  const savedLang = localStorage.getItem('selectedLang') || 'en';

  this.translate.addLangs(supportedLangs);
  this.translate.setDefaultLang('en');
  this.translate.use(savedLang);
}
}
