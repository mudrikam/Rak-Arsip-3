import os
from datetime import datetime

class MarkdownGenerator:
    def __init__(self):
        pass
    
    def generate_project_markdown(self, name, root, category, subcategory, date_path, full_path, color="#7bb205"):
        """Generate markdown file for a project based on the standard template"""
        
        # Parse date from date_path (e.g., "2025\\July\\11" -> "2025-07-11")
        date_parts = date_path.split("\\") if date_path else []
        formatted_date = self._format_date_for_frontmatter(date_parts)
        
        # Generate tags
        tags = self._generate_tags(root, category, subcategory, date_parts)
        
        # Generate frontmatter
        frontmatter = self._generate_frontmatter(root, category, subcategory, formatted_date, tags)
        
        # Generate directory section
        directory_section = self._generate_directory_section(full_path, name, color)
        
        # Generate preview section
        preview_section = self._generate_preview_section(name, color)
        
        # Combine all sections
        markdown_content = f"{frontmatter}\n\n{directory_section}\n\n{preview_section}"
        
        return markdown_content
    
    def _format_date_for_frontmatter(self, date_parts):
        """Convert date parts to YYYY-MM-DD format"""
        if len(date_parts) >= 3:
            year = date_parts[0]
            month = date_parts[1]
            day = date_parts[2]
            
            # Convert month name to number
            month_map = {
                'January': '01', 'February': '02', 'March': '03', 'April': '04',
                'May': '05', 'June': '06', 'July': '07', 'August': '08',
                'September': '09', 'October': '10', 'November': '11', 'December': '12',
                'Januari': '01', 'Februari': '02', 'Maret': '03', 'April': '04',
                'Mei': '05', 'Juni': '06', 'Juli': '07', 'Agustus': '08',
                'September': '09', 'Oktober': '10', 'November': '11', 'Desember': '12'
            }
            
            month_num = month_map.get(month, '01')
            day_padded = day.zfill(2)
            
            return f"{year}-{month_num}-{day_padded}"
        else:
            # Fallback to current date
            return datetime.now().strftime("%Y-%m-%d")
    
    def _generate_tags(self, root, category, subcategory, date_parts):
        """Generate tags list"""
        tags = []
        
        if category:
            tags.append(category)
        if subcategory:
            tags.append(subcategory)
        if root:
            tags.append(root)
        
        # Add date-based tags
        if len(date_parts) >= 3:
            year, month, day = date_parts[:3]
            tags.append(f"{year}_{month}_{day}")
            tags.append(month)
        
        return tags
    
    def _generate_frontmatter(self, root, category, subcategory, formatted_date, tags):
        """Generate YAML frontmatter"""
        frontmatter = "---\n"
        frontmatter += f'Lokasi: "[[{root}]]"\n'
        frontmatter += f'Kategori: "[[{category}]]"\n'
        frontmatter += f'Sub_Kategori: "[[{subcategory}]]"\n'
        frontmatter += f'Tanggal_Buat: {formatted_date}\n'
        frontmatter += "Tags:\n"
        
        for tag in tags:
            frontmatter += f"  - {tag}\n"
        
        frontmatter += "Selesai: false\n"
        frontmatter += "---"
        
        return frontmatter
    
    def _generate_directory_section(self, full_path, name, color):
        """Generate directory file section"""
        section = f'## <span style="color:{color}">Direktori File</span> :\n\n'
        section += "---\n\n"
        section += "```\n"
        section += f"{full_path}\n"
        section += "```\n\n"
        section += "```\n"
        section += f"{name}\n"
        section += "```\n\n"
        section += f"[Buka Folder]({full_path})"
        
        return section
    
    def _generate_preview_section(self, name, color):
        """Generate preview section"""
        section = f'## <span style="color:{color}">Preview</span> :\n\n'
        section += "---\n\n"
        section += f"![[{name}.png]]"
        
        return section
    
    def create_markdown_file(self, folder_path, name, root, category, subcategory, date_path, full_path, color="#7bb205"):
        """Create markdown file in the specified folder"""
        try:
            markdown_content = self.generate_project_markdown(
                name, root, category, subcategory, date_path, full_path, color
            )
            
            markdown_filename = f"{name}.md"
            markdown_filepath = os.path.join(folder_path, markdown_filename)
            
            with open(markdown_filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            return markdown_filepath
            
        except Exception as e:
            print(f"Error creating markdown file: {e}")
            return None
