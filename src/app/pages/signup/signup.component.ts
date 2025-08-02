import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Router, RouterModule } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-signup',
  standalone: true,
  imports: [FormsModule, RouterModule,TranslateModule],
  templateUrl: './signup.component.html',
  styleUrls: ['./signup.component.css']
})
export class SignupComponent {
  name: string = '';
  email: string = '';
  password: string = '';
  contact: string = '';

  constructor(
  private http: HttpClient,
  private router: Router,
  private translate: TranslateService
) {
  const supportedLangs = ['en', 'hin', 'fr', 'de', 'pl'];
  const lang = (typeof window !== 'undefined' && localStorage.getItem('selectedLang')) 
    ? localStorage.getItem('selectedLang')!
    : 'en';

  this.translate.addLangs(supportedLangs);
  this.translate.setDefaultLang('en');
  this.translate.use(lang);
}

  onSignup() {
    const signupData = {
      name: this.name,
      email: this.email,
      password: this.password,
      contact_number: this.contact
    };

    const passwordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
    if (!passwordPattern.test(this.password)) {
      alert(this.translate.instant('signup.error.weakPassword'));
      return;
    }

    this.http.post('http://127.0.0.1:5000/user/patient-signup', signupData).subscribe(
      () => {
        alert(this.translate.instant('signup.success'));
        this.router.navigate(['/login']);
      },
      (error) => {
        console.error('Signup error:', error);
        alert(this.translate.instant('signup.error.failed'));
      }
    );
  }
}
