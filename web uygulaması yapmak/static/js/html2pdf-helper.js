/**
 * PDF Oluşturma Yardımcı Fonksiyonları
 * html2pdf.js kütüphanesini kullanarak HTML içeriğini PDF'e dönüştürür
 */

// PDF oluşturma fonksiyonu
function createPDF(contentElement, filename, callback) {
    // PDF içeriğini hazırla
    const content = prepareContent(contentElement);
    
    // PDF oluşturma seçenekleri
    const options = {
        margin: [15, 15, 15, 15],
        filename: filename || 'belge.pdf',
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { 
            scale: 2, 
            useCORS: true,
            letterRendering: true,
            logging: false
        },
        jsPDF: { 
            unit: 'mm', 
            format: 'a4', 
            orientation: 'portrait' 
        }
    };
    
    // PDF oluştur ve indir
    return html2pdf()
        .from(content)
        .set(options)
        .save()
        .then(() => {
            if (typeof callback === 'function') {
                callback(true);
            }
            return true;
        })
        .catch(err => {
            console.error('PDF oluşturma hatası:', err);
            if (typeof callback === 'function') {
                callback(false, err);
            }
            return false;
        });
}

// CV içeriğini PDF için hazırlayan fonksiyon
function prepareContent(element) {
    // Element bir string ise, DOM elemanı oluştur
    if (typeof element === 'string') {
        const div = document.createElement('div');
        div.innerHTML = element;
        element = div;
    }
    
    // Element kopyasını oluştur
    const container = element.cloneNode(true);
    
    // PDF için stil ekle
    const style = document.createElement('style');
    style.textContent = `
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            padding: 10px;
        }
        h1, h2, h3, h4 {
            color: #1a73e8;
            font-weight: 600;
            margin-top: 15px;
        }
        h1 {
            font-size: 22px;
            border-bottom: 2px solid #1a73e8;
            padding-bottom: 8px;
        }
        h2 {
            font-size: 18px;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 5px;
        }
        h3 {
            font-size: 16px;
        }
        ul {
            margin-left: 20px;
            padding-left: 20px;
        }
        li {
            margin-bottom: 5px;
        }
        .skill-tag { 
            display: inline-block; 
            background-color: #e8f0fe; 
            color: #1a73e8; 
            padding: 2px 8px; 
            border-radius: 15px; 
            margin: 2px; 
            font-size: 14px; 
        }
    `;
    
    container.prepend(style);
    
    // Markdown formatını temizle
    container.innerHTML = container.innerHTML
        .replace(/\n\n/g, '<br><br>')  // Çift satır boşluklarını br'ye dönüştür
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // Kalın metni formatla
        .replace(/\*(.*?)\*/g, '<em>$1</em>');  // İtalik metni formatla
        
    // Becerileri etiketlere dönüştür
    container.innerHTML = container.innerHTML.replace(
        /([a-zA-ZğüşıöçĞÜŞİÖÇ\s]+)(,|\s-\s|;)/g,
        '<span class="skill-tag">$1</span>$2'
    );
    
    return container;
}

// Buton durumunu güncelleyen yardımcı fonksiyon
function updateButtonStatus(button, isLoading, originalText) {
    if (isLoading) {
        button.innerHTML = '<i style="margin-right: 5px;">⏳</i> PDF Hazırlanıyor...';
        button.disabled = true;
        button.style.opacity = '0.7';
    } else {
        button.innerHTML = originalText || '<i style="margin-right: 5px;">📥</i> PDF İndir';
        button.disabled = false;
        button.style.opacity = '1';
    }
} 